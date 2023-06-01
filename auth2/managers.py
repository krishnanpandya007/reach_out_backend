# from django.core.serializers.json import Djan
# from .models import TimedProfilePoint

# class LazyEncoder(DjangoJSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, TimedProfilePoint):
#             return {"profile_id": obj.pk, "day": obj.added_at.day, "month": obj.added_at.month, "year": obj.added_at.year}
#         return super().default(obj)


# class LazyDecoder(DjangoJSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, TimedProfilePoint):
#             return {"profile_id": obj.pk, "day": obj.added_at.day, "month": obj.added_at.month, "year": obj.added_at.year}
#         return super().default(obj)