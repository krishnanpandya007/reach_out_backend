'''
This file consists of small testing snippets.
'''


# from pymemcache.client.base import Client

# client = Client(('localhost', 11211))

# client.set('message', "Krishnan")

# print(client.get('message'))

# import memcache

# memc = memcache.Client(['127.0.0.1:11211'], debug=1)
# memc.set('a', 100)
# print(memc.get('a'))
# from functools import wraps
# from typing import Callable, Any, Union
# from pymemcache.client.base import Client

# # # print()

# client = Client(('127.0.0.1', 11211))
# client.set('message', "Hello")
# print(client.get('message'))
# from auth2.views import render

# print(render)
# class memcache:

#     @staticmethod
#     def set_new(cache_type:str) -> Any:
#         def inner_parent(cache_getter_func:Callable[[str, str], Any]) -> Any:

#             @wraps(cache_getter_func)
#             def inner(*args, **kwargs):
#                 print("Validating...")
#                 cache_key = args[0]
#                 otp =  cache_getter_func(*args, **kwargs) #  Here it must return cache_value if none, itll consider as failure to generate cacheKey and won't store in memcache
#                 if(otp == None):
#                     print("GOt None as cache_value, skipping to store it in memCache")
#                     return None
#                 print("GOT OTP:", "%s:%s" % (cache_type, cache_key))
#                 print("Setting to memcache Layer")
#                 return otp

#             return inner

#         return inner_parent


#     @staticmethod
#     def set_new(cache_type:str) -> Any:
#         def inner_parent(cache_getter_func:Callable[[str, str], Any]) -> Any:

#             @wraps(cache_getter_func)
#             def inner(*args, **kwargs):
#                 print("Validating...")
#                 cache_key = args[0]
#                 otp =  cache_getter_func(*args, **kwargs) #  Here it must return cache_value if none, itll consider as failure to generate cacheKey and won't store in memcache
#                 if(otp == None):
#                     print("GOt None as cache_value, skipping to store it in memCache")
#                     return None
#                 print("GOT OTP:", "%s:%s" % (cache_type, cache_key))
#                 print("Setting to memcache Layer")
#                 return otp

#             return inner

#         return inner_parent

# def validate_cache_key(cache_getter_func):

#     @wraps(cache_getter_func)
#     def inner(*args, **kwargs):
#         print("Validating...")

#         if(len(args) < 1):
#             raise Exception('Func must be built with initial arg with cache_key')

#         if(not isinstance(args[0], str)):
#             raise Exception('cache_key must be type of `str`')

#         print(args, kwargs)
#         return cache_getter_func(*args, **kwargs)

#     return inner

# @memcache.set_new(cache_type='otp')
# @validate_cache_key
# def generate_otp(username:str) -> Union[int, None]:
#     return 3124

# print(generate_otp("krishnan"))
# ------------STOP_---------------------
# from http.server import BaseHTTPRequestHandler, HTTPServer
# import time

# hostName = "localhost"
# serverPort = 11211


# class MyServer(BaseHTTPRequestHandler):
#     def do_GET(self):
#         self.send_response(200)
#         self.send_header("Content-type", "text/html")
#         self.end_headers()
#         self.wfile.write(bytes("<html><head><title>https://pythonbasics.org</title></head>", "utf-8"))
#         self.wfile.write(bytes("<p>Request: %s</p>" % self.path, "utf-8"))
#         self.wfile.write(bytes("<body>", "utf-8"))
#         self.wfile.write(bytes("<p>This is an example web server.</p>", "utf-8"))
#         self.wfile.write(bytes("</body></html>", "utf-8"))

# if __name__ == "__main__":        
#     webServer = HTTPServer((hostName, serverPort), MyServer)
#     print("Server started http://%s:%s" % (hostName, serverPort))

#     try:
#         webServer.serve_forever()
#     except KeyboardInterrupt:
#         pass

#     webServer.server_close()
#     print("Server stopped.")

# import socket
# import sys

# HOST = '127.0.0.1'	# Symbolic name, meaning all available interfaces
# PORT = 11211	# Arbitrary non-privileged port

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# print('Socket created')

# #Bind socket to local host and port
# try:
# 	s.bind((HOST, PORT))
# except socket.error as msg:
# 	print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
# 	sys.exit()
	
# print('Socket bind complete')

# #Start listening on socket
# s.listen(10)
# print('Socket now listening')

# #now keep talking with the client
# while 1:
#     #wait to accept a connection - blocking call
# 	conn, addr = s.accept()
# 	print('Connected with ' + addr[0] + ':' + str(addr[1]))
	
# s.close()

# import  auth2.backends 
# --------------------------
# GET ADMIN PASS
# 
# from os import getenv
# from hashlib import sha512
# m = sha512()
# m.update(bytes("staff0krishnanpandya",'utf-8'))
# m.update(bytes(getenv('STAFF_PASSWORD_TRANSACTION_KEY', 'vn36DIW!N*Zn2&$nh!rZ3A&k3CykzLE2PpC5QfNBjyq^%2WYF9'),'utf-8'))
# print(m.hexdigest())
'''
---------------------------
'''
# from requests import post
# from base64 import b64encode
# encoded_credentials = b64encode("6RtN9k7U2WudB3OX2dYrarPnucJXnKny45iSoWpR:nNfdrOB13AIRvfg93xeD0DYP3XUsgD5weZqIHptieiPnT024UN8kgmFXVqcHqN5r53fhLT3ARBRCjP5wttBXkQCvXeVPf7ElJ1aBC2PS51IyWhlGl2UGdvRQEatQjZdF".encode('ascii'))
# d = encoded_credentials.decode('ascii')
# response = post('http://localhost:8000/o/token/', data={'grant_type': 'refresh_token', 'refresh_token': 'G0rCEajgqgxJkf42d7Pl3NhuEZ8oit','client_id': '6RtN9k7U2WudB3OX2dYrarPnucJXnKny45iSoWpR', 'client_secret': 'rViCcY2pIWi7OsmjP7xXeo8FrULV1ouXWfxVuGqejWzlcC2FrC4Wc4mBHDmqG4bMOSf4f3wijiQmGWAbV2tSvWzfYUq3NR0gcUcrotRFgG6cKXybBiesVI3ny6Gzg0UY'})

# print(response.status_code)
# print(response.json())
'''
---------------------------
'''

# import os
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reach_out_backend.settings")

# import django
# django.setup()

# from django.db import transaction
# from auth2.models import Phone, Profile

# '''
# TODO: in Profile make a method, update_ip which takes IPV4 and updates accordingly
# '''

# def get_client_ip(request):
#     x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#     if x_forwarded_for:
#         ip = x_forwarded_for.split(',')[0]
#     else:
#         ip = request.META.get('REMOTE_ADDR')
#     return ip

# phon = Phone.objects.create(number='8qd8asssd89')
# with transaction.atomic():
#     a = Profile.objects.create(first_name='Krishnan', last_name='Pandya', email='daqs@gtr.com', phone=phon)
#     a.raw_ip = '1.1.1.1'
#     a.save()
# phon = Phone.objects.create(number='8qd8asssd89')
# with transaction.atomic():
#     a = Profile.objects.get(username='krishnanpandya19')
#     a.raw_ip = '1.1.1.1'
#     a.save()

'''
9510539042
95105 39042
'''

def format_phone_number(contact_number:str, client_country_calling_code:str):

    if(" " in contact_number[-10:]):
        contact_number = contact_number[:-10] + contact_number[-10:].replace(' ', '-')
    if("-" not in contact_number[-10:]):
        contact_number = contact_number[:-5] + '-' +  contact_number[-5:]
    print(contact_number)
    if("+" not in contact_number):
        contact_number = client_country_calling_code + " " + contact_number
    else:
        if(contact_number[-12] != ' '):
            contact_number = contact_number[:-11] + ' ' + contact_number[-11:]
    return contact_number

