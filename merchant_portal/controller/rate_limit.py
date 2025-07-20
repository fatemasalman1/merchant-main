import functools
from functools import wraps
from typing import Callable

import frappe
from frappe import _


def rate_limit_exponential(
    key: str | None = None,
    *,
    limit: int = 5,
    window: int = 60,
    base_penalty: int = 120,
    max_strikes: int = 10,
    strike_window: int = 24 * 60 * 60,
    methods: str | list = "ALL",
    ip_based: bool = True,
):
    """
    Rate-limit with exponential backoff and 24h strike reset.

    :param key:           form_dict key to distinguish callers (e.g. "user_id" or "api_key")
    :param limit:         max requests allowed within `window`
    :param window:        time-window in seconds for counting requests
    :param base_penalty:  seconds to block on first breach (doubles each subsequent strike)
    :param max_strikes:   maximum number of recorded strikes (caps the exponent)
    :param strike_window: how long (secs) to remember strikes; defaults to 24 h
    :param methods:       "ALL" or list of HTTP methods to enforce
    :param ip_based:      whether to include client IP in the identity
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Skip if not an HTTP request or method not in scope
            req = getattr(frappe, "request", None)
            if not req or (
                methods != "ALL"
                and req.method.upper() not in (methods if isinstance(methods, (list, tuple)) else [methods])
            ):
                return fn(*args, **kwargs)

            # Build unique identity
            ip = frappe.local.request_ip if ip_based else None
            user_key = frappe.form_dict.get(key, "") if key else None
            if key and ip_based:
                identity = f"{ip}:{user_key}"
            else:
                identity = ip or user_key
            if not identity:
                frappe.throw(_("Either key or IP flag is required."))

            cmd = frappe.form_dict.get("cmd", fn.__name__)
            cache = frappe.cache

            # Redis keys
            count_key   = cache.make_key(f"rl:count:{cmd}:{identity}")
            strikes_key = cache.make_key(f"rl:strikes:{cmd}:{identity}")
            block_key   = cache.make_key(f"rl:block:{cmd}:{identity}")

            # 1) If currently blocked, refuse immediately
            if cache.get(block_key):
                frappe.throw(
                    _("Rate limit exceeded. Please try again later."),
                    frappe.RateLimitExceededError
                )

            # 2) Count calls in this window
            cnt = cache.get(count_key) or 0
            if cnt == 0:
                cache.setex(count_key, window, 0)
            cnt = cache.incrby(count_key, 1)

            # 3) On breach → apply exponential penalty
            if cnt > limit:
                strikes = int(cache.get(strikes_key) or 0)
                strikes = min(strikes, max_strikes)
                penalty = base_penalty * (2 ** strikes)

                # set block and bump strike count
                cache.setex(block_key, penalty, 1)
                cache.setex(strikes_key, strike_window, strikes + 1)

                frappe.throw(
                    _("Rate limit exceeded; you’re blocked for {0} seconds.").format(penalty),
                    frappe.RateLimitExceededError
                )

            # 4) Under the limit → proceed
            return fn(*args, **kwargs)

        return wrapper
    return decorator
