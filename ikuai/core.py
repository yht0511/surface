import base64
import hashlib
import json
from datetime import datetime
from urllib.parse import quote, urljoin

import requests

from .constants import (JSON_RESPONSE_DATA, JSON_RESPONSE_ERRMSG,
                        JSON_RESPONSE_ERRMSG_SUCCESS, JSON_RESPONSE_RESULT,
                        acl_l7_param, acl_l7_param_action, acl_mac_param,
                        domain_blacklist_param, json_result_code,
                        mac_comment_param, mac_group_param, mac_qos_param,
                        rp_action, rp_func_name, rp_key, rp_order_param,
                        url_black_param)
from .exceptions import (AuthenticationError, RequestError, RouterAPIError,
                         ValidationError)


class QueryRPParam:
    def __init__(
            self, param_type=None,
            limit=None, order_by=None, order_param=None):
        """
        :param param_type: list
        :param limit: list of int
        :param order_by: string
        :param order_param: string
        """

        if param_type is not None:
            assert isinstance(param_type, list), "param_type must be a list"
        self.param_type = param_type or ["total", "data"]

        if limit is not None:
            assert isinstance(limit, list), "limit must be a list"
            assert len(limit) == 2,  (
                "limit must be a list with 2 elements which denote "
                "start number and end number")
        self.limit = limit or [0, 100]

        if order_by:
            assert isinstance(order_by, str), (
                "order_by must be a string which denote the field to be sorted")
        self.order_by = order_by or ""

        if order_param:
            assert isinstance(order_param, str), (
                "order_param must be a string which denote how the field "
                "will be sorted")
            assert order_param in [rp_order_param.asc, rp_order_param.desc]
        self.order_param = order_param or ""

    def as_dict(self):
        return {
            "TYPE": ",".join(self.param_type),
            "limit": ",".join(map(str, self.limit)),
            "ORDER_BY": self.order_by,
            "ORDER": self.order_param
        }


class IKuaiClient:  # noqa
    def __init__(self, url, username, password):
        self._username = username
        self._passwd = password
        self.base_url = url.strip().rstrip("/")
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = requests.session()
            self.authenticate()

        return self._session

    def authenticate(self):
        passwd = hashlib.md5(self._passwd.encode()).hexdigest()
        pass_encoded = base64.b64encode(f'salt_11{passwd}'.encode()).decode()
        login_info = {
            'passwd': passwd,
            'pass': pass_encoded,
            'remember_password': "",
            'username': self._username
        }
        self._session = requests.session()

        response = (
            self._session.post(f'{self.base_url}/Action/login', json=login_info))
        if response.status_code != 200:
            self._session = None
            raise AuthenticationError(
                f"Failed to authenticate with status code {response.status_code}")

        content = response.json()
        if content[JSON_RESPONSE_RESULT] != json_result_code.code_10000:
            self._session = None
            raise AuthenticationError(
                "Failed to authenticate with result code "
                f"{content[JSON_RESPONSE_RESULT]}: {content[JSON_RESPONSE_ERRMSG]}."
            )

    def list_protocols_json(self):
        response = self.session.get(
            urljoin(self.base_url, "json/protocols_cn.json"), headers={
                "Content-Type": 'application/json'
            })
        if response.status_code == 200:
            return response.json()
        raise RequestError(
            f"Request failed with response status code: {response.status_code}")

    def exec(self, func_name, action, param, ensure_success=True):
        payload = {
            rp_key.func_name: func_name,
            rp_key.action: action,
            rp_key.param: param
        }
        response = self.session.post(
            urljoin(self.base_url, "/Action/call"), json=payload, headers={
                "Content-Type": 'application/json'
            })
        if response.status_code == 200:
            try:
                content = response.json()
                if not ensure_success:
                    return content

                if content[JSON_RESPONSE_ERRMSG] == JSON_RESPONSE_ERRMSG_SUCCESS:
                    return content
                else:
                    if content[JSON_RESPONSE_ERRMSG] == "no login authentication":
                        self._session = None
                        return self.exec(func_name, action, param, ensure_success)
                    raise RouterAPIError(
                        f"API result error: '{content[JSON_RESPONSE_ERRMSG]}': "
                        f"{repr(content)}"
                    )
            except json.JSONDecodeError:
                # the response is not a valid json
                if 'sending to kernel ...' in response.content.decode():
                    return json.loads(
                        response.content.decode().replace(
                            "sending to kernel ...", "").replace("\n", ""))

                raise RequestError(
                    f"Error parsing response: {response.content.decode()}")

        raise RequestError(
            f"Request failed with response status code: {response.status_code}")

    @staticmethod
    def validate_weekday(weekdays_str):
        input_chars_set = set(weekdays_str)
        invalid_chars = input_chars_set - set("1234567")

        if invalid_chars:
            raise ValueError(
                f"weekdays str contains invalid characters: {invalid_chars}")

        sorted_unique_chars = sorted(input_chars_set)
        return ''.join(sorted_unique_chars)

    @staticmethod
    def validate_time_range(time_range_str):
        # 分割字符串以检查两个时间
        parts = time_range_str.split("-")
        if len(parts) != 2:
            raise ValidationError(
                "time format error: it must be of format 'HH:MM-HH:MM'")

        # 验证时间格式
        time_format = "%H:%M"
        start_time_str, end_time_str = parts
        try:
            # 尝试将字符串转换为时间对象以验证格式和范围
            start_time = datetime.strptime(start_time_str, time_format)  # noqa
            end_time = datetime.strptime(end_time_str, time_format)  # noqa
        except Exception as e:
            # 如果转换失败，说明时间格式不正确
            raise ValidationError(f"time format error: {type(e).__name__}: {str(e)}")

        # 可选: 检查开始时间是否早于或等于结束时间
        # if start_time > end_time:
        #     return False
        return

    # {{{ mac group CRUD

    def add_mac_group(self, group_name, addr_pools, comments=None):
        comments = comments or []
        return self.exec(
            func_name=rp_func_name.macgroup,
            action=rp_action.add,
            param={
                mac_group_param.newRow: True,
                mac_group_param.group_name: group_name,
                mac_group_param.addr_pool: ",".join(addr_pools),
                mac_group_param.comment: (f",{quote(' ')}".join(comments))
            }
        )

    def list_mac_groups(self, **query_kwargs):
        result = self.exec(
            func_name=rp_func_name.macgroup,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def edit_mac_group(self, group_id, group_name, addr_pools, comments=None):
        comments = comments or []
        return self.exec(
            func_name=rp_func_name.macgroup,
            action=rp_action.edit,
            param={
                mac_group_param.id: group_id,
                mac_group_param.group_name: group_name,
                mac_group_param.addr_pool: ",".join(addr_pools),
                mac_group_param.comment: (f",{quote(' ')}".join(comments))
            }
        )

    def del_mac_group(self, group_id):
        return self.exec(
            func_name=rp_func_name.macgroup,
            action=rp_action.delete,
            param={
                mac_group_param.id: group_id,
            }
        )

    # }}}

    # {{{ acl_l7 CRUD
    # 行为管控 之 应用协议控制

    def _get_acl_l7_param(
            self, comment, src_addrs: list, action,
            dst_addrs=None,
            prio=32, app_protos=None, enabled=True, time="00:00-23:59",
            week="1234567"):

        self.validate_time_range(time)
        self.validate_weekday(week)

        app_protos = app_protos or []
        enabled = "yes" if enabled else "no"
        comment = comment.replace(" ", quote(" "))
        assert action in [acl_l7_param_action.accept, acl_l7_param_action.drop]

        dst_addrs = dst_addrs or []
        dst_addr = ",".join(dst_addrs)

        src_addr = ",".join(src_addrs)

        param = {
            acl_l7_param.action: action,
            acl_l7_param.app_proto: ",".join(app_protos),
            acl_l7_param.comment: comment,
            acl_l7_param.dst_addr: dst_addr or "",
            acl_l7_param.enabled: enabled,
            acl_l7_param.prio: prio,
            acl_l7_param.src_addr: src_addr,
            acl_l7_param.time: time,
            acl_l7_param.week: week
        }
        return param

    def add_acl_l7(self, comment, src_addrs, action, dst_addrs=None,
                   prio=32, app_protos=None, enabled=True, time="00:00-23:59",
                   week="1234567"):

        param = self._get_acl_l7_param(
            comment, src_addrs, action, dst_addrs, prio,
            app_protos, enabled, time, week)

        return self.exec(
            func_name=rp_func_name.acl_l7,
            action=rp_action.add,
            param=param
        )

    def list_acl_l7(self, **query_kwargs):
        result = self.exec(
            func_name=rp_func_name.acl_l7,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def edit_acl_l7(self, acl_l7_id, comment, src_addrs, action, dst_addrs=None,
                    prio=32, app_protos=None, enabled=True, time="00:00-23:59",
                    week="1234567"):
        param = self._get_acl_l7_param(
            comment, src_addrs, action, dst_addrs, prio,
            app_protos, enabled, time, week)

        param[acl_l7_param.id] = acl_l7_id

        return self.exec(
            func_name=rp_func_name.acl_l7,
            action=rp_action.edit,
            param=param
        )

    def del_acl_l7(self, acl_l7_id):
        return self.exec(
            func_name=rp_func_name.acl_l7,
            action=rp_action.delete,
            param={
                acl_l7_param.id: acl_l7_id,
            }
        )

    def disable_acl_l7(self, acl_l7_id):
        return self.exec(
            func_name=rp_func_name.acl_l7,
            action=rp_action.down,
            param={
                acl_l7_param.id: acl_l7_id,
            }
        )

    def enable_acl_l7(self, acl_l7_id):
        return self.exec(
            func_name=rp_func_name.acl_l7,
            action=rp_action.up,
            param={
                acl_l7_param.id: acl_l7_id,
            }
        )

    # }}}

    # {{{ domain_blacklist CRUD
    # 行为管控 之 禁止娱乐网站

    def _get_domain_blacklist_param(
            self, enabled=True,
            ipaddrs=None,
            domain_groups=None, time="00:00-23:59",
            comment=None,
            weekdays="1234567"):

        self.validate_time_range(time)
        self.validate_weekday(weekdays)

        domain_groups = domain_groups or []
        enabled = "yes" if enabled else "no"
        comment = comment or []
        comment = comment.replace(" ", quote(" "))

        ipaddrs = ipaddrs or []
        ipaddr = ",".join(ipaddrs)

        param = {
            domain_blacklist_param.comment: comment,
            domain_blacklist_param.domain_group: ",".join(domain_groups),
            domain_blacklist_param.enabled: enabled,
            domain_blacklist_param.ipaddr: ipaddr,
            domain_blacklist_param.time: time,
            domain_blacklist_param.weekdays: weekdays
        }
        return param

    def list_domain_blacklist(self, **query_kwargs):
        result = self.exec(
            func_name=rp_func_name.domain_blacklist,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def add_domain_blacklist(
            self, enabled=True,
            ipaddrs=None,
            domain_groups=None, time="00:00-23:59",
            comment=None,
            weekdays="1234567"):

        param = self._get_domain_blacklist_param(
            enabled=enabled,
            ipaddrs=ipaddrs,
            domain_groups=domain_groups,
            time=time,
            comment=comment,
            weekdays=weekdays)

        return self.exec(
            func_name=rp_func_name.domain_blacklist,
            action=rp_action.add,
            param=param
        )

    def edit_domain_blacklist(
            self, domain_blacklist_id, enabled=True,
            ipaddrs=None,
            domain_groups=None, time="00:00-23:59",
            comment=None,
            weekdays="1234567"):

        param = self._get_domain_blacklist_param(
            enabled=enabled,
            ipaddrs=ipaddrs,
            domain_groups=domain_groups,
            time=time,
            comment=comment,
            weekdays=weekdays)

        param[domain_blacklist_param.id] = domain_blacklist_id

        return self.exec(
            func_name=rp_func_name.domain_blacklist,
            action=rp_action.edit,
            param=param
        )

    def del_domain_blacklist(self, domain_blacklist_id):
        return self.exec(
            func_name=rp_func_name.domain_blacklist,
            action=rp_action.delete,
            param={
                domain_blacklist_param.id: domain_blacklist_id,
            }
        )

    def disable_domain_blacklist(self, domain_blacklist_id):
        return self.exec(
            func_name=rp_func_name.domain_blacklist,
            action=rp_action.down,
            param={
                domain_blacklist_param.id: domain_blacklist_id,
            }
        )

    def enable_domain_blacklist(self, domain_blacklist_id):
        return self.exec(
            func_name=rp_func_name.domain_blacklist,
            action=rp_action.up,
            param={
                domain_blacklist_param.id: domain_blacklist_id,
            }
        )

    # }}}

    def get_sysstat(self, param_types=None):
        param_types = param_types or "verinfo,cpu,memory,stream,cputemp".split(",")
        result = self.exec(
            func_name=rp_func_name.sysstat,
            action=rp_action.show,
            param={"TYPE": ",".join(param_types)}
        )
        return result[JSON_RESPONSE_DATA]

    def list_monitor_lanip(self, ip_type="v4", **query_kwargs):
        assert ip_type in ["v4", "v6"], "ip_type must be 'v4' or 'v6'"

        result = self.exec(
            func_name=(rp_func_name.monitor_lanip if ip_type == "v4"
                       else rp_func_name.monitor_lanipv6),
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    # {{{ mac_comment CRUD
    # 行为管控 之 终端名称管理

    def list_mac_comment(self, **query_kwargs):
        # mac comment will override device ip info comment
        result = self.exec(
            func_name=rp_func_name.mac_comment,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def del_mac_comment(self, mac_comment_id):
        return self.exec(
            func_name=rp_func_name.mac_comment,
            action=rp_action.delete,
            param={
                mac_comment_param.id: mac_comment_id,
            }
        )

    def add_mac_comment(self, mac, comment):
        return self.exec(
            func_name=rp_func_name.mac_comment,
            action=rp_action.add,
            param={
                mac_comment_param.mac: mac,
                mac_comment_param.comment: comment
            }
        )

    def edit_mac_comment(self, mac_comment_id, mac, comment):
        return self.exec(
            func_name=rp_func_name.mac_comment,
            action=rp_action.edit,
            param={
                mac_comment_param.id: mac_comment_id,
                mac_comment_param.mac: mac,
                mac_comment_param.comment: comment
            }
        )

    # }}}

    # {{{ acl_mac CRUD
    # 行为管控 之 MAC访问控制

    def _get_acl_mac_param(
            self,
            mac,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567"):

        self.validate_time_range(time)
        self.validate_weekday(week)

        enabled = "yes" if enabled else "no"
        comment = comment or ""
        comment = comment.replace(" ", quote(" "))

        param = {
            acl_mac_param.mac: mac,
            acl_mac_param.comment: comment,
            acl_mac_param.enabled: enabled,
            acl_mac_param.time: time,
            acl_mac_param.week: week
        }
        return param

    def list_acl_mac(self, **query_kwargs):
        result = self.exec(
            func_name=rp_func_name.acl_mac,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def add_acl_mac(
            self,
            mac,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567"):

        param = self._get_acl_mac_param(
            mac=mac,
            enabled=enabled,
            time=time,
            comment=comment,
            week=week)

        return self.exec(
            func_name=rp_func_name.acl_mac,
            action=rp_action.add,
            param=param
        )

    def edit_acl_mac(
            self,
            acl_mac_id,
            mac,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567"):

        param = self._get_acl_mac_param(
            mac=mac,
            enabled=enabled,
            time=time,
            comment=comment,
            week=week)

        param[acl_mac_param.id] = acl_mac_id

        return self.exec(
            func_name=rp_func_name.acl_mac,
            action=rp_action.edit,
            param=param
        )

    def del_acl_mac(self, acl_mac_id):
        return self.exec(
            func_name=rp_func_name.acl_mac,
            action=rp_action.delete,
            param={
                acl_mac_param.id: acl_mac_id,
            }
        )

    def disable_acl_mac(self, acl_mac_id):
        return self.exec(
            func_name=rp_func_name.acl_mac,
            action=rp_action.down,
            param={
                acl_mac_param.id: acl_mac_id,
            }
        )

    def enable_acl_mac(self, acl_mac_id):
        return self.exec(
            func_name=rp_func_name.acl_mac,
            action=rp_action.up,
            param={
                acl_mac_param.id: acl_mac_id,
            }
        )

    # }}}

    # {{{ mac_qos CRUD
    # 流控分流 之 MAC限速

    def list_mac_qos(self, **query_kwargs):
        result = self.exec(
            func_name=rp_func_name.mac_qos,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def _get_mac_qos_param(
            self,
            mac_addrs,
            upload,
            download,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567",
            qos_type=0,
            ip_type="4",
            is_editing=False,
            mac_qos_id=None,
            interface=None,
    ):

        if not isinstance(mac_addrs, list):
            mac_addrs = [mac_addrs]

        mac_addr = ",".join(mac_addrs)

        interface = interface or []
        if not isinstance(interface, list):
            interface = [interface]
        interface = ",".join(interface)

        upload = float(upload)
        download = float(download)

        # qos_type: "0" for 独立限速, "1" for 共享限速
        assert qos_type in [0, 1, "0", "1"]
        qos_type = str(qos_type)

        assert ip_type in ["4", "6", 4, 6]
        ip_type = str(ip_type)

        self.validate_time_range(time)
        self.validate_weekday(week)

        enabled = "yes" if enabled else "no"
        comment = comment or ""
        comment = comment.replace(" ", quote(" "))

        param = {
            mac_qos_param.mac_addr: mac_addr,
            mac_qos_param.comment: comment,
            mac_qos_param.enabled: enabled,
            mac_qos_param.time: time,
            mac_qos_param.week: week,
            mac_qos_param.qos_type: qos_type,
            mac_qos_param.ip_type: ip_type,
            mac_qos_param.upload: upload,
            mac_qos_param.download: download,
            mac_qos_param.interface: interface,
        }

        # when edit, there's a attr=0 param
        if is_editing:
            assert mac_qos_id is not None, (
                "mac_qos_param_id cannot be None when editing")

            param[mac_qos_param.id] = mac_qos_id
            param[mac_qos_param.attr] = 0

        """
        attr: 0
        comment: "快速添加"
        download: 10000
        enabled: "yes"
        id: 1
        interface: "wan1"
        ip_type: "4"
        mac_addr: "45:a9:fd:43:97:2c,test2"
        time: "00:00-23:59"
        type: 1
        upload: 10000
        week: "1234567"
        """

        return param

    def add_mac_qos(
            self,
            mac_addrs,
            upload,
            download,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567",
            qos_type=0,
            ip_type="4",
            interface=None):

        param = self._get_mac_qos_param(
            mac_addrs=mac_addrs,
            upload=upload,
            download=download,
            enabled=enabled,
            time=time,
            comment=comment,
            week=week,
            qos_type=qos_type,
            ip_type=ip_type,
            is_editing=False,
            interface=interface
        )

        return self.exec(
            func_name=rp_func_name.mac_qos,
            action=rp_action.add,
            param=param
        )

    def edit_mac_qos(
            self,
            mac_qos_id,
            mac_addrs,
            upload,
            download,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567",
            qos_type=0,
            ip_type="4",
            interface=None):

        param = self._get_mac_qos_param(
            mac_addrs=mac_addrs,
            upload=upload,
            download=download,
            enabled=enabled,
            time=time,
            comment=comment,
            week=week,
            qos_type=qos_type,
            ip_type=ip_type,
            is_editing=True,
            interface=interface,
            mac_qos_id=mac_qos_id
        )

        return self.exec(
            func_name=rp_func_name.mac_qos,
            action=rp_action.edit,
            param=param
        )

    def del_mac_qos(self, mac_qos_id):
        return self.exec(
            func_name=rp_func_name.mac_qos,
            action=rp_action.delete,
            param={
                mac_qos_param.id: mac_qos_id,
            }
        )

    def disable_mac_qos(self, mac_qos_id):
        return self.exec(
            func_name=rp_func_name.mac_qos,
            action=rp_action.down,
            param={
                mac_qos_param.id: mac_qos_id,
            }
        )

    def enable_mac_qos(self, mac_qos_id):
        return self.exec(
            func_name=rp_func_name.mac_qos,
            action=rp_action.up,
            param={
                mac_qos_param.id: mac_qos_id,
            }
        )

    # }}}

    # {{{ url_black CRUD
    # 行为管控 之 网址黑名单

    def list_url_black(self, **query_kwargs):
        result = self.exec(
            func_name=rp_func_name.url_black,
            action=rp_action.show,
            param=QueryRPParam(**query_kwargs).as_dict()
        )
        return result[JSON_RESPONSE_DATA]

    def _get_url_black_param(
            self,
            ip_addrs,
            mode,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567",
            is_editing=False,
            url_black_id=None):

        if not isinstance(ip_addrs, list):
            ip_addrs = [ip_addrs]
        ip_addr = ",".join(ip_addrs)

        # mode: "0" for 独立限速, "1" for 共享限速
        assert mode in [0, 1, "0", "1"]
        mode = int(mode)

        self.validate_time_range(time)
        self.validate_weekday(week)

        enabled = "yes" if enabled else "no"
        comment = comment or ""
        comment = comment.replace(" ", quote(" "))

        param = {
            url_black_param.ip_addr: ip_addr,
            url_black_param.comment: comment,
            url_black_param.enabled: enabled,
            url_black_param.mode: mode,
            url_black_param.time: time,
            url_black_param.week: week,
        }

        # when edit, there's a attr=0 param
        if is_editing:
            assert url_black_id is not None, (
                "mac_qos_param_id cannot be None when editing")

            param[url_black_param.id] = url_black_id
        return param

    def add_url_black(
            self,
            ip_addrs,
            mode,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567"):

        param = self._get_url_black_param(
            ip_addrs=ip_addrs,
            mode=mode,
            enabled=enabled,
            time=time,
            comment=comment,
            week=week,
            is_editing=False,
        )

        return self.exec(
            func_name=rp_func_name.url_black,
            action=rp_action.add,
            param=param
        )

    def edit_url_black(
            self,
            url_black_id,
            ip_addrs,
            mode,
            enabled=True,
            time="00:00-23:59",
            comment=None,
            week="1234567"):

        param = self._get_url_black_param(
            ip_addrs=ip_addrs,
            mode=mode,
            enabled=enabled,
            time=time,
            comment=comment,
            week=week,
            is_editing=True,
            url_black_id=url_black_id
        )

        return self.exec(
            func_name=rp_func_name.url_black,
            action=rp_action.edit,
            param=param
        )

    def del_url_black(self, url_black_id):
        return self.exec(
            func_name=rp_func_name.url_black,
            action=rp_action.delete,
            param={
                url_black_param.id: url_black_id,
            }
        )

    def disable_url_black(self, url_black_id):
        return self.exec(
            func_name=rp_func_name.url_black,
            action=rp_action.down,
            param={
                url_black_param.id: url_black_id,
            }
        )

    def enable_url_black(self, url_black_id):
        return self.exec(
            func_name=rp_func_name.url_black,
            action=rp_action.up,
            param={
                url_black_param.id: url_black_id,
            }
        )

    def list_vwanips(self):
        res=self.exec(
            func_name=rp_func_name.vwanips,
            action=rp_action.show,
            param={
                "TYPE": "vlan_data,vlan_total",
                "interface": "wan1",
                "limit": "0,20",
                "ORDER_BY": "id",
                "ORDER": "desc",
                "vlan_internet": 1
            }
        )
        ans=[]
        for i in res["Data"]["vlan_data"]:
            ans.append(i["dhcp_ip_addr"])
        return ans
    
    def wake_on_lan(self,MAC):
        res=self.exec(
            func_name=rp_func_name.wake,
            action=rp_action.wake,
            param={
                "mac": MAC,
            }
        )
        if res["ErrMsg"]=="Success":
            return True
        return False
    # }}}