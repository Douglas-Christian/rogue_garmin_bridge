import json
import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return str(obj)
        return super(DateTimeEncoder, self).default(obj)

def json_serialize(data):
    """Serialize data to JSON with proper handling of datetime objects."""
    return json.dumps(data, cls=DateTimeEncoder)
