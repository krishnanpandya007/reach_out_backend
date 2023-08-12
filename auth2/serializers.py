from rest_framework.serializers import ModelSerializer, ReadOnlyField, SerializerMethodField, IntegerField
from .models import Profile, Social, Preference

class QuickSocialSerializer(ModelSerializer):

    '''
    Gives a quick overview of a social by providing social media name and profileUrl to that
    '''

    # profile_link = ReadOnlyField()

    class Meta:
        model = Social
        fields = ['socialMedia', 'profile_link']


class ProfileSerializer(ModelSerializer):
    '''
    Use to generate profile Card information (ShortView)
    '''

    name = ReadOnlyField(source='get_full_name')
    socials = QuickSocialSerializer(many=True, read_only=True)
    reached = SerializerMethodField('_check_reached')
    profilePicUrl = ReadOnlyField(source='safe_profile_pic_url')

    class Meta:
        model = Profile
        fields = ['id', 'name', 'bio', 'socials', 'reached', 'profilePicUrl']

    def _check_reached(self, obj):

        current_profile_id = self.context.get("profile_id", -1)

        if(current_profile_id == -1): return False

        reached_ids = [user.pk for user in list(obj.reachers.all())]

        if(current_profile_id in reached_ids):
            # Reached ✅
            return True

        return False

        # in creation take, name, email, phone_no, password. take up custom create mathod to handle phone_no



class ProfilePageSerializer(ModelSerializer):

    name = ReadOnlyField(source='get_full_name')
    profilePicUrl = ReadOnlyField(source='safe_profile_pic_url')
    reaches = IntegerField(
        source='reachers.count', 
        read_only=True
    )
    reached = SerializerMethodField('_check_reached')
    socials = QuickSocialSerializer(many=True, read_only=True)
    marked = SerializerMethodField('_check_marked')
    

    class Meta:
        model = Profile
        fields = ['name', 'bio', 'profilePicUrl', 'reaches', 'reached', 'socials', 'marked']

    def _check_reached(self, obj):

        current_profile_id = self.context.get("profile_id", -1)

        if(current_profile_id == -1): return False

        reached_ids = [user.pk for user in list(obj.reachers.all())]

        if(current_profile_id in reached_ids):
            # Reached ✅
            return True

        return False


    def _check_marked(self, obj):

        current_profile_id = self.context.get("profile_id", -1)

        if(current_profile_id == -1): return False

        profile = Profile.objects.get(pk=current_profile_id)

        return profile.marks.contains(obj)
    
class ProfilePreferencesSerializer(ModelSerializer):

    class Meta:
        
        model = Preference
        fields = '__all__'
        