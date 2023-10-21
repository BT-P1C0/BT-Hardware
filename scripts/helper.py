from env import env
import json


# environment variable to python object
class ObjectFromDict(object):
    """
    Convert python dictionary to object
    """

    def __init__(self, data: dict):
        for key, val in data.items():
            setattr(self, key, self.__compute_attr_value(val))

    def __compute_attr_value(self, value):
        if type(value) is list or type(value) is tuple:
            return [self.__compute_attr_value(x) for x in value]
        elif type(value) is dict:
            return ObjectFromDict(value)
        else:
            return value


channel = "bus_" + env.id.busNo


def httpGetUrl(lat: float, lng: float, utc: float):
    payload = f"%7B%22lat%22%3A{lat}%2C%22lng%22%3A{lng}%2C%22utc%22%3A{utc}%7D"
    return f"http://ps.pndsn.com/publish/{env.pubnub.pk}/{env.pubnub.sk}/0/{channel}/0/{payload}?uuid={env.id.uuid}"


def crashUrl(lat: float, lng: float, utc: float):
    payload = f"%7B%22bus%22%3A%22{env.id.busNo}%22%2C%22lat%22%3A{lat}%2C%22lng%22%3A{lng}%2C%22utc%22%3A{utc}%7D"
    return f"http://ps.pndsn.com/publish/{env.pubnub.pk}/{env.pubnub.sk}/0/crash_notification/0/{payload}?uuid={env.id.uuid}"


def debugGetUrl(status: str, RSSI):
    payload = f"%7B%0A%20%20%20%20%22bus%22%3A%20%22{env.id.busNo}%22%2C%0A%20%20%20%20%22status%22%3A%20%22{status}%22%2C%0A%20%20%20%20%22RSSI%22%3A%20%22{RSSI}%22%0A%7D"
    return f"http://ps.pndsn.com/publish/{env.pubnub.pk}/{env.pubnub.sk}/0/debug_channel/0/{payload}?uuid={env.id.uuid}"


def debugPostUrl():
    return f"http://ps.pndsn.com/publish/{env.pubnub.pk}/{env.pubnub.sk}/0/debug_channel/0/?uuid={env.id.uuid}"


def debugPostPayload(status: str, RSSI, lat: float, lng: float, time: str):
    payload = {
        "bus": env.id.busNo,
        "status": status,
        "rssi": RSSI,
        "lat": lat,
        "lng": lng,
        "time": time,
    }
    return json.dumps(payload)


if __name__ == "__main__":
    pass
