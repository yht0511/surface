JSON_RESPONSE_RESULT = "Result"
JSON_RESPONSE_ERRMSG = "ErrMsg"
JSON_RESPONSE_ERRMSG_SUCCESS = "Success"
JSON_RESPONSE_DATA = "Data"


class json_result_code:  # noqa
    code_10001 = 10001
    code_10000 = 10000
    code_30000 = 30000


class rp_key:  # noqa
    action = "action"
    func_name = "func_name"
    param = "param"


class rp_action:  # noqa
    show = "show"
    add = "add"
    edit = "edit"
    delete = "del"
    up = "up"
    down = "down"
    wake = "wake_mac"


class rp_func_name:  # noqa
    sysstat = "sysstat"

    macgroup = "macgroup"
    mac_comment = "mac_comment"
    mac_qos = "mac_qos"

    domain_blacklist = "domain_blacklist"
    monitor_lanip = "monitor_lanip"
    monitor_lanipv6 = "monitor_lanipv6"

    acl_l7 = "acl_l7"
    acl_mac = "acl_mac"

    url_black = "url_black"

    vwanips = "wan"
    
    wake = "wakeup"

class rp_order_param:  # noqa
    asc = "asc"
    desc = "desc"


class mac_group_param:  # noqa
    id = "id"
    group_name = "group_name"
    addr_pool = "addr_pool"
    comment = "comment"
    newRow = "newRow"


class acl_l7_param:  # noqa
    id = "id"
    action = "action"
    app_proto = "app_proto"
    comment = "comment"
    dst_addr = "dst_addr"
    enabled = "enabled"
    prio = "prio"
    src_addr = "src_addr"
    time = "time"
    week = "week"


class acl_l7_param_action:  # noqa
    drop = "drop"
    accept = "accept"


class domain_blacklist_param:  # noqa
    id = "id"
    comment = "comment"
    domain_group = "domain_group"
    enabled = "enabled"
    ipaddr = "ipaddr"
    time = "time"
    weekdays = "weekdays"


class mac_comment_param:  # noqa
    id = "id"
    mac = "mac"
    comment = "comment"


class acl_mac_param:  # noqa
    id = "id"
    comment = "comment"
    enabled = "enabled"
    mac = "mac"
    time = "time"
    week = "week"


class mac_qos_param:  # noqa
    attr = "attr"  # todo: what does this control?
    id = "id"
    comment = "comment"
    enabled = "enabled"
    download = "download"
    upload = "upload"
    interface = "interface"
    mac_addr = "mac_addr"
    time = "time"
    week = "week"
    qos_type = "type"
    ip_type = "ip_type"


class url_black_param:  # noqa
    id = "id"
    comment = "comment"
    domain = "domain"
    enabled = "enabled"
    ip_addr = "ip_addr"
    mode = "mode"
    time = "time"
    week = "week"
    