from django.shortcuts import render

# Create your views here.

'''
Suggested: must read this app's __init__.py doc. in order to get blueprint whole workflow
'''




'''
Example Workflow

class UnlockAnalytics(APIView):

    permission_classes = (AllowAny,)

    def get(self, request):
        try:

            # Get the prices of plan
            return Response({'error': False, 'message': 'Retrieved analytics plans!', 'prices': ANALYTICS_PLAN_PRICES}, status=200)

        except Exception as e:
            return Response({'error': True, 'message': 'Something went wrong!'},status=500)

'''