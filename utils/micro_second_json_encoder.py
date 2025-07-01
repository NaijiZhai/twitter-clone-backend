import datetime

from django.core.serializers.json import DjangoJSONEncoder



class MicrosecondEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)
