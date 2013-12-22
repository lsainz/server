# -*- encoding: utf-8 -*-

from django import forms
from nexmo import NexmoMessage
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
#from django.forms import CharField,Form,PasswordInput
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from taxiexpress.models import Customer, Country, State, City, Driver
from taxiexpress.serializers import CustomerSerializer, DriverSerializer
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance, D
#from django.core import serializers
#from django.core.validators import validate_email
#from django.core.exceptions import ValidationError
#import json
import random
import string
import pytz
from datetime import datetime
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from emailusernames.utils import create_user
from emailusernames.utils import get_user, user_exists
from django.contrib.auth import authenticate


# Create your views here.
@csrf_exempt
@api_view(['POST'])
def loginUser(request):
    user = authenticate(email=request.POST['email'], password=request.POST['password'])
    if user:
        customer = user.customer
        if customer.phone != request.POST['phone']:
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content=("Credenciales incorrectas phone" + customer.phone + request.POST['phone']))
        request.session['email'] = customer.email
        request.session['user_id'] = customer.id
        datetime_request = datetime.strptime(request.POST['lastUpdate'], '%Y-%m-%d %H:%M:%S')
        utc=pytz.UTC
        now_aware = utc.localize(datetime_request)
        if customer.lastUpdate > now_aware:
            serialCustomer = CustomerSerializer(customer)
            return Response(serialCustomer.data, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_200_OK)
    else:
        return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="Credenciales incorrectas")


@csrf_exempt
def registerUser(request):
    if request.method == "POST":
        passtemp = request.POST['password'];
        if user_exists(request.POST['email']):
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="Email en uso")
        if (Customer.objects.filter(phone=request.POST['phone']).count() > 0):
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="Teléfono en uso")
        #elif (passtemp.length() < 4)
        #   return HttpResponse("shortpassword", content_type="text/plain")
        else:
            try:
                u = create_user(request.POST['email'], passtemp)
                c = Customer(user = u, phone=request.POST['phone'], lastUpdate=datetime.strptime(request.POST['lastUpdate'], '%Y-%m-%d %H:%M:%S'))
                code = random.randint(1, 999999)
                c.validationCode = code
                c.save()
                msg = {
                        'reqtype': 'json',
                        'api_key': '8a352457',
                        'api_secret': '460e58ff',
                        'from': '619317759',
                        'to': equest.POST['phone'],
                        'text': 'Su codigo de validacion de Taxi Express es: ' + code
                    }
                
                sms = NexmoMessage(msg)
                sms.set_text_info(msg['text'])

                response = sms.send_request()

                # Falta saber si devuelve un JSON o un XML, depende de la API a la que haga la POST la libreria.

                
                return HttpResponse(status=status.HTTP_201_CREATED)
            except ValidationError:
                HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="Email no válido")
    else:
        HttpResponse(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def getClosestTaxi(request):
    if request.GET.get('latitud', "false") != "false":
        pointclient = Point(float(request.GET['latitud']), float(request.GET['longitud']))

        list_TaxiDrivers = Driver.objects.distance(pointclient).order_by('distance')[0]

@api_view(['GET'])
def test(request):
    user = get_user('gorka_12@hotmail.com')
    cu = user.customer
    lista = cu.favlist.all()
    return HttpResponse(status=status.HTTP_200_OK,content=lista)

        #return JSON with taxi info

@api_view(['GET'])
def validateUser(request):
    #IMPORTANTE, el contenido del email no es correcto, hay que actualizarlo.
    if request.method == "GET":
        if request.GET['phone'] is None:
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="Telefono incorrecto")
        try:
            customer = Customer.objects.get(phone=request.GET['phone'])  
        except ObjectDoesNotExist:
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="No es posible validar a este usuario")
        if customer.validationCode == request.GET['validationCode']:
            customer.isValidated = True
            subject = 'Parking Express: Tu contraseña ha sido modificada'
            from_email = 'MyTaxiExpress@gmail.com'
            to = [customer.email]
            html_content = 'Bienvenido a Taxi Express! <br> <br> Para comenzar a utilizar nuestros servicios deberás confirmar tu dirección de correo eletrónico haciendo click en el siguiente enlace: <br> <br> <a href="https://manage.stripe.com/confirm_email?t=z5roGRDbZdRbvknLfTZHCUSCyvPeznIw"> <br> <br> Un saludo de parte del equipo de Taxi Express.'
            msg = EmailMessage(subject, html_content, from_email, to)
            msg.content_subtype = "html"  # Main content is now text/html
            msg.send()
            return HttpResponse(status=status.HTTP_201_CREATED,content="El usuario ha sido validado correctamente")
        else:
            return HttpResponse(status=status.HTTP_401_UNAUTHORIZED, content="No es posible validar a este usuario")

@api_view(['POST'])
@csrf_exempt
def changePassword(request):
    #IMPORTANTE, el contenido del email no es correcto, hay que actualizarlo.
    user = authenticate(email=request.POST['email'], password=request.POST['password'])
    if user:
        user.password = request.POST['newPass']  
        user.save()
        subject = 'Taxi Express: Tu contraseña ha sido modificada'
        from_email = 'MyTaxiExpress@gmail.com'
        to = [customer.email]
        html_content = 'Le informamos de que su contraseña de Taxi Express ha sido modificada. En el caso en el que no tenga constancia de ello, pongase inmediantamente en contactocon MyTaxiExpress@gmail.com.'
        msg = EmailMessage(subject, html_content, from_email, to)
        msg.content_subtype = "html"  # Main content is now text/html
        msg.send()  
        return HttpResponse(status=201,content="La contraseña ha sido modificada correctamente")
    else:
        return HttpResponse(status=401, content="Credenciales incorrectas")

@api_view(['POST'])
@csrf_exempt
def updateProfile(request):
    user = get_user(request.POST['email'])
    if request.session['email'] == user.email:
        user.first_name = request.POST['firstName']
        user.last_name = request.POST['lastName']
        user.customer.image = request.POST['newImage']
        user.save()
        return HttpResponse(status=201,content="Perfil del usuario modificado correctamente")
    else:
        return HttpResponse(status=401, content="El email introducido no es válido")
    

@api_view(['POST'])
@csrf_exempt
def addFavoriteDriver(request):
    try:
        customer = Customer.objects.get(email=request.POST['customerEmail'])
    except ObjectDoesNotExist:
        return HttpResponse(status=401, content="El usuario introducido no es válido")
    try:
        driver = Customer.objects.get(email=request.POST['driverEmail'])
    except ObjectDoesNotExist:
        return HttpResponse(status=401, content="El taxista introducido no es válido")
    customer.favlist.add(driver)
    customer.save()
    return HttpResponse(status=201,content="Taxista añadido a la lista de favoritos")


@api_view(['POST'])
@csrf_exempt
def removeFavoriteDriver(request):
        try:
            customer = Customer.objects.get(email=request.POST['customerEmail'])
        except ObjectDoesNotExist:
            return HttpResponse(status=401, content="El usuario introducido no es válido")
        try:
            driver = customer.favlist.get(email=request.POST['driverEmail'])
        except ObjectDoesNotExist:
            return HttpResponse(status=401, content="El taxista no se encuentra en tu lista de favoritos")
        customer.favlist.remove(driver)
        customer.save()
        return HttpResponse(status=201,content="Taxista eliminado de la lista de favoritos")


@api_view(['GET'])
def loadData(request):
    co = Country(code = 108,name='Espana')
    co.save()
    s = State(code = 48, name = 'Bizkaia', country = co)
    s.save()
    ci = City(code = 013, name = 'Barakaldo', state = s)
    ci.save()
    ci = City(code = 015, name = 'Basauri', state = s)
    ci.save()
    ci = City(code = 016, name = 'Berango', state = s)
    ci.save()
    ci = City(code = 017, name = 'Bermeo', state = s)
    ci.save()
    ci = City(code = 020, name = 'Bilbao', state = s)
    ci.save()
    ci = City(code = 027, name = 'Durango', state = s)
    ci.save()
    ci = City(code = 036, name = 'Galdakao', state = s)
    ci.save()
    ci = City(code = 040, name = 'Gatika', state = s)
    ci.save()
    ci = City(code = 043, name = 'Gorliz', state = s)
    ci.save()
    ci = City(code = 044, name = 'Getxo', state = s)
    ci.save()
    ci = City(code = 046, name = 'Gernika-Lumo', state = s)
    ci.save()
    ci = City(code = 054, name = 'Leioa', state = s)
    ci.save()
    ci = City(code = 057, name = 'Lekeitio', state = s)
    ci.save()
    ci = City(code = 065, name = 'Ugao-Miraballes', state = s)
    ci.save()
    ci = City(code = 78, name = 'Portugalete', state = s)
    ci.save()
    ci = City(code = 81, name = 'Lezama', state = s)
    ci.save()
    ci = City(code = 82, name = 'Santurtzi', state = s)
    ci.save()
    ci = City(code = 84, name = 'Sestao', state = s)
    ci.save()
    ci = City(code = 85, name = 'Sopelana', state = s)
    ci.save()
    ci = City(code = 89, name = 'Urduliz', state = s)
    ci.save()
    us = create_user('conductor@gmail.com', '1111')
    us.first_name="Conductor"
    us.last_name="DePrimera"
    us.save()
    dr = Driver(user=us, phone="656111112", city=ci)
    dr.save()
    us = create_user('conductor2@gmail.com', '1111')
    us.first_name="Conductor"
    us.last_name="DeSegunda"
    us.save()
    dr2 = Driver(user=us, phone="656111113", city=ci)
    dr2.save()
    us = create_user('gorka_12@hotmail.com', '1111')
    us.first_name="Pepito"
    us.last_name="Palotes"
    us.save()
    cu = Customer(user=us, phone="656111111", city=ci, lastUpdate=datetime.strptime('1980-01-01 00:00:01','%Y-%m-%d %H:%M:%S'))
    cu.save()
    cu.favlist.add(dr)
    cu.favlist.add(dr2)
    return HttpResponse(status=201,content="Cargado")
