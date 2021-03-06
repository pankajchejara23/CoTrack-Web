from django.shortcuts import render
from django.http import HttpResponse
from .forms import CreateForm1,CreateForm2,CreateForm3,CreateForm4, lastForm, AnonyForm, SessionForm, AudioflForm, VADForm
from formtools.wizard.views import SessionWizardView
from django import forms
from django.db import transaction
from .models import Project, Survey, Pad, Link, Submission, Session, SessionPin, SessionGroupMap, AuthorMap, VAD
from django.contrib import messages
import uuid
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect
from django.db.models import Count
from datetime import date
from django.db import transaction
import uuid
from django.core.files.storage import FileSystemStorage
from .models import Audiofl
import datetime
import re
from django.conf import settings
import time
import csv
from django.contrib.auth import login as auth_login

from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
################### Changeset Processing ######################
def changeset_parse (c) :
    changeset_pat = re.compile(r'^Z:([0-9a-z]+)([><])([0-9a-z]+)(.+?)\$')
    op_pat = re.compile(r'(\|([0-9a-z]+)([\+\-\=])([0-9a-z]+))|([\*\+\-\=])([0-9a-z]+)')

    def parse_op (m):
        g = m.groups()
        if g[0]:
            if g[2] == "+":
                op = "insert"
            elif g[2] == "-":
                op = "delete"
            else:
                op = "hold"
            return {
                'raw': m.group(0),
                'op': op,
                'lines': int(g[1], 36),
                'chars': int(g[3], 36)
            }
        elif g[4] == "*":
            return {
                'raw': m.group(0),
                'op': 'attr',
                'index': int(g[5], 36)
            }
        else:
            if g[4] == "+":
                op = "insert"
            elif g[4] == "-":
                op = "delete"
            else:
                op = "hold"
            return {
                'raw': m.group(0),
                'op': op,
                'chars': int(g[5], 36)
            }

    m = changeset_pat.search(c)
    bank = c[m.end():]
    g = m.groups()
    ops_raw = g[3]
    op = None

    ret = {}
    ret['raw'] = c
    ret['source_length'] = int(g[0], 36)
    ret['final_op'] = g[1]
    ret['final_diff'] = int(g[2], 36)
    ret['ops_raw'] = ops_raw
    ret['ops'] = ops = []
    ret['bank'] = bank
    ret['bank_length'] = len(bank)
    for m in op_pat.finditer(ops_raw):
        ops.append(parse_op(m))
    return ret

def perform_changeset_curline (text, c):
    textpos = 0
    curline = 0
    curline_charpos = 0
    curline_insertchars = 0
    bank = c['bank']
    bankpos = 0
    newtext = ''
    current_attributes = []

    # loop through the operations
    # rebuilding the final text
    for op in c['ops']:
        if op['op'] == "attr":
            current_attributes.append(op['index'])
        elif op['op'] == "insert":
            newtextposition = len(newtext)
            insertion_text = bank[bankpos:bankpos+op['chars']]
            newtext += insertion_text
            bankpos += op['chars']
            if 'lines' in op:
                curline += op['lines']
                curline_charpos = 0
            else:
                curline_charpos += op['chars']
                curline_insertchars = op['chars']
            # todo PROCESS attributes
            # NB on insert, the (original/old/previous) textpos does *not* increment...
        elif op['op'] == "delete":
            newtextposition = len(newtext) # is this right?
            # todo PROCESS attributes
            textpos += op['chars']

        elif op['op'] == "hold":
            newtext += text[textpos:textpos+op['chars']]
            textpos += op['chars']
            if 'lines' in op:
                curline += op['lines']
                curline_charpos = 0
            else:
                curline_charpos += op['chars']

    # append rest of old text...
    newtext += text[textpos:]
    return newtext, curline, curline_charpos, curline_insertchars
###############################################################

def isTeacher(request):
    current_user = request.user
    role = Role.objects.get(user=current_user)
    if role == 'teacher':
        return True
    else:
        return False


CREATE_FORMS = (
    ("questionnaire", CreateForm1),
    ("product", CreateForm2),
    ("participants", CreateForm3),
    ("editq", CreateForm4),
    ("overview",lastForm))

TEMPLATES = {"questionnaire": "create.html",
             "product": "create.html",
             "participants": "create.html",
             "editq": "create.html",
             "overview": "overview.html"}



import os
from django.core.files.base import File
from django.shortcuts import render, redirect
import requests

# Etherpad interacting function
def call(function,arguments=None,request=None):
    try:
        url = settings.ETHERPAD_URL + '/api/1.2.12/' +function+'?apikey='+settings.ETHERPAD_KEY
        response = requests.post(url,arguments)
        x = response.json()
        print('Returned:x',x)
        return x
    except:
        messages.error(request,'The etherpad server is not accessible. Please check your etherpad server and configuration.')
        return redirect('project_home')




def model_form_upload(request):
    if request.method == 'POST':
        form = AudioflForm(request.POST, request.FILES)
        print('function called')
        if form.is_valid():
            newform = form.save(commit=False)
            print('valid form')
            djfile = File(request.FILES['fl'])
            newform.fl.save(request.FILES['fl'].name, djfile)
            newform.save()
            print('data saved')

            # convert to fix the duration of audio
            file_path = newform.fl.path
            #os.system("/usr/bin/mv %s %s" % (file_path, (file_path + '.original')))
            #os.system("/usr/bin/ffmpeg -i %s -c copy -fflags +genpts %s" % ((file_path + '.original'), file_path))

            return redirect('/')
    else:
        form = AudioflForm()
    return render(request, 'model_form_upload.html', {
        'form': form
    })


def list_files(request):
    files = Audiofl.objects.all().order_by('uploaded_at')

    return render(request, 'list_files.html', {
        'files': files
    })




def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def getAnonyForm(request):
    if request.method == "POST":
        form = AnonyForm(request.POST)
        return HttpResponse('submitted')
    else:
        form = AnonyForm()
        return render(request,"anonymous-form.html",{'form':form})


# View to generate report for specific project_type
def getReport(request):
    ################################

    # code to generate report here




    ##################################
    return HttpResponse('Report will be provided here')

@transaction.atomic
def createSession(request):

    print('function view called')
    if request.method == "POST":
        form = SessionForm(request.POST)
        print(form)
        if form.is_valid():
            current_user = request.user
            s_name = form.cleaned_data['name']
            s_groups = form.cleaned_data['groups']
            s_description = form.cleaned_data['problem']
            s = Session.objects.create(owner=current_user,name = s_name,groups = s_groups, problem = s_description)

            ######### Creating pads on Etherpad #################


            x = call('createGroup',request=request)
            print(x)
            if (x["code"] == 0):
                groupid = x["data"]["groupID"]
                print('Group created successfully:',groupid)
                sgm = SessionGroupMap.objects.create(session=s,eth_groupid=x["data"]["groupID"])

                for g in range(s_groups):
                    g =  g + 1
                    pad_name = 'session_'+str(s.id)+'_'+'group'+'_'+str(g)
                    print(' Creating pad:',pad_name,' with Groupid:',groupid)
                    res = call('createGroupPad',{'groupID':groupid,'padName':pad_name},request=request)
                    print(res)
                    if res and res["code"] == 0:
                        Pad.objects.create(session=s,eth_padid=res['data']['padID'],group=g)
                        print('Pad created:',g)
                    else:
                        messages.error(request,'Error occurred while creating pads. Check your Etherpad server settings.')
                        return redirect('project_home')
            else:
                messages.error(request,'Error occurred while creating groups. Check your Etherpad server settings.')

                return redirect('project_home')


            #####################################################
            while True:
                u_pin = uuid.uuid4().hex[:6].upper()
                objs = SessionPin.objects.filter(pin = u_pin)
                if objs.count() == 0:
                    break
            pin_obj = SessionPin.objects.create(session=s,pin=u_pin)
            messages.success(request, 'Session created successfully !')
            return redirect('project_home')

        else:
            print('invalid data')
    else:

        form = SessionForm()
        return render(request,'session.html',{'form':form,'edit':False})



@transaction.atomic
def editSession(request,session_id):
    if request.method == "POST":
        form = SessionForm(request.POST)
        print(form)
        if form.is_valid():
            current_user = request.user
            s_name = form.cleaned_data['name']
            s_groups = form.cleaned_data['groups']
            s_description = form.cleaned_data['problem']
            s_id = form.cleaned_data['id']

            s_object = Session.objects.get(id=session_id)

            if(s_object.groups > s_groups):
                messages.error(request,'Reducing the number of groups will results in lost of data if some data has already been collected. Therefore at the moment CoTrack does not save the updation which reduces the number of groups.')
                return redirect('project_home')

            extra_groups = s_groups - s_object.groups



            sgm = SessionGroupMap.objects.filter(session=session_id)

            for g in range(extra_groups):
                g =  g + 1 + s_object.groups
                pad_name = 'session_'+str(session_id)+'_'+'group'+'_'+str(g)
                print(' Creating pad:',pad_name,' with Groupid:',sgm[0].eth_groupid)
                res = call('createGroupPad',{'groupID':sgm[0].eth_groupid,'padName':pad_name},request=request)
                print(res)
                if res and res["code"] == 0:
                    Pad.objects.create(session=session_id,eth_padid=res['data']['padID'],group=g)
                    print('Pad created:',g)
                else:
                    messages.error(request,'Error occurred while creating pads. Check your Etherpad server settings.')
                    return redirect('project_home')

            s_object.name = s_name
            s_object.groups = s_groups
            s_object.problem = s_description

            s_object.save()


            messages.success(request, 'Session edited successfully !')
            return redirect('project_home')

        else:
            print('invalid data')
    else:
        print('Session edit:',session_id)
        s_object = Session.objects.get(id=session_id)

        if(s_object.owner != request.user):
            messages.error(request,'You do not have permission for specified session.')
            return redirect('project_home')

        s_name = s_object.name
        s_groups = s_object.groups
        s_description = s_object.problem


        form = SessionForm(initial={'name':s_name,'groups':s_groups,'problem':s_description,'id':session_id})
        return render(request,'session.html',{'form':form,'edit':True})



def sessionFilter(request,filter):

    if filter not in ['all','archived']:
        messages.error(request,'Incorrect filter applied.')
        return redirect('project_home')
    else:
        projects = []
        if filter == 'archived':
            sessions = Session.objects.all().filter(status=True)
            if sessions.count() == 0:
                messages.warning(request,'There are no archived project')
            else:
                msg = 'Archived sessions are fetched successfully!'
                messages.success(request,msg)
            return render(request, "dashboard.html",{'sessions':sessions,'filter':True})

        else:
            messages.success(request,'All sessions are fetched successfully')
            return redirect('project_home')



def sessionAction(request,session_id,type):
    if type not in ['archived','all']:
        messages.error(request,'Unsupported action.')

    else:
        try:
            s_object = Session.objects.get(id=session_id)
        except Project.DoesNotExist:
            messages.error(request,'Session id does not exists.')

        if s_object is not None:
            if type == 'archive':
                s_object.archived = True
            else:
                s_object.archived = False
            s_object.save()
            msg = 'session '+session.name+' has been ' +type+'d successfully!'
            messages.success(request,msg)

    return redirect('project_home')

def surveyForm(request,link):
    if request.method == "POST":
        q1 = int(request.POST['q1'])
        q2 = int(request.POST['q2'])
        q3 = int(request.POST['q3'])
        q4 = int(request.POST['q4'])
        q5 = int(request.POST['q5'])
        q6 = int(request.POST['q6'])
        q7 = int(request.POST['q7'])
        q8 = int(request.POST['q8'])
        q9 = int(request.POST['q9'])
        q10 = int(request.POST['q10'])
        q11 = int(request.POST['q7'])
        q12 = int(request.POST['q8'])
        q13 = int(request.POST['q9'])
        q14 = int(request.POST['q10'])

        link_obj = Link.objects.get(url=link)
        submission = Submission.objects.create(link=link_obj,q1=q1,q2=q2,q3=q3,q4=q4,q5=q5,q6=q6,q7=q7,q8=q8,q9=q9,q10=q10,q11=q11,q12=q12,q13=q13,q14=q14)

        return getAnonyForm(request)
    else:
        return render(request,"survey_form.html",{'product':'Smartphone','title':'Measure the Trust'})

def generateSurvey(request,link):
    if not is_valid_uuid(link):
        return render(request, "survey_msg.html",{'msg_title':'Invalid Link','msg_body':'The survey link is invalid.'})

    survey_url = Link.objects.all().filter(url=link)

    if survey_url.count() == 0:
        return render(request, "survey_msg.html",{'msg_title':'Invalid Link','msg_body':'The survey link is invalid.'})
    else:
        survey_url = Link.objects.get(url=link)

        if survey_url.survey.project.project_status:
            variables = {
                "PROJECT_NAME":survey_url.survey.project.project_name,
                "PRODUCT_NAME":survey_url.survey.product_name,
                "PRODUCT_INDUSTRY":survey_url.survey.product_industry,
                "TODAY":date.today(),
                "SURVEY_NAME":survey_url.survey.survey_name,
            }
            print(variables)
            title = survey_url.survey.title
            subtitle = survey_url.survey.subtitle
            paragraph = survey_url.survey.paragraph

            title = title.format(**variables)
            subtitle = subtitle.format(**variables)
            paragraph = paragraph.format(**variables)


            return render(request,"survey_front.html",{'project_title':title,'subtitle':subtitle,'paragraph':paragraph,'link':survey_url.url})
        else:
            return render(request, "survey_msg.html",{'msg_title':'Not active','msg_body':'The survey is not active.'})










# Create your views here.
def overview(request):
    sessions = Session.objects.all().filter(owner=request.user)
    print(sessions.count())
    return render(request, "dashboard.html",{'sessions':sessions,'filter':False})

def enterForm(request):
    if request.method == "POST":
        request.session.flush()


        s_pin = request.POST['pin']

        session = SessionPin.objects.all().filter(pin=s_pin)
        if session.count() == 0:
            messages.error(request,'Entered pin is invalid.')

            request.user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, request.user)

            return render(request,"session_student_entry_v2.html",{})
        else:
            session_obj = SessionPin.objects.get(pin=s_pin)

            user = request.user

            res = call('createAuthorIfNotExistsFor',{'authorMapper':user.id,'name':user.first_name})

            print(res)

            authorid = res['data']['authorID']

            group = SessionGroupMap.objects.get(session=session_obj.session)
            groupid = group.eth_groupid

            NextDay_Date = datetime.datetime.today() + datetime.timedelta(days=1)


            res2 = call('createSession',{'authorID':authorid,'groupID':groupid,'validUntil':NextDay_Date.timestamp()})
            print('=================>Session')
            print(res2)





            request.session['joined'] = session_obj.session.id
            request.session['ethsid'] = res2['data']['sessionID']
            request.user.backend = 'django.contrib.auth.backends.ModelBackend'

            auth_login(request,request.user)



            groups = range(session_obj.session.groups)

            response = render(request,'student_session_home.html',{'session':session_obj.session,'groups':groups})

            response.set_cookie('joined_session',session_obj.session.id)
            response.set_cookie('sessionID',res2['data']['sessionID'])
            return response
    else:
        print('Get method')
        if 'joined' in request.session.keys():
            print('cookie exists')
            session_obj = SessionPin.objects.get(id=request.session['joined'])
            groups = range(session_obj.session.groups)
            return render(request,'student_session_home.html',{'session':session_obj.session,'groups':groups})
        else:

            return render(request,"session_student_entry_v2.html",{})


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def getRevCount(request,padid):
    params = {'padID':padid}
    rev_count = call('getRevisionsCount',params)
    return Response({'revisions':rev_count['data']['revisions']})


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def getTime(request):
    print('getTime called')
    if 't' in request.GET:
        t = request.query_params.get('t')
        t = int(t)

        print('Client:',t)
        cs = datetime.datetime.now()
        print('Server:',cs)
        current_time = int(cs.timestamp())*1000 # convert into millisecons
        current_time += cs.microsecond/1000 # getting millisecons
        print('Server milli:',current_time)
        delta = int(current_time) - t/1000
        print('delta:',delta)
        print('Returned:',str(delta),':',str(t))
        res = str(delta),':',str(t)
        return Response({'offset':int(delta),'time':t})





@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def getGroupPadStats(request,padid):
    params = {'padID':padid}
    rev_count = call('getRevisionsCount',params)
    # get user wise Info
    print(call('padUsersCount',params))
    print(call('listAuthorsOfPad',params))

    author_list = call('listAuthorsOfPad',params)['data']['authorIDs']

    addition = {}
    deletion = {}

    author_names = {}

    for author in author_list:
        print('Author',author)
        addition[author] = 0
        deletion[author] = 0

        author_names[author] = call('getAuthorName',{'authorID':author})['data']
        #author_obj = AuthorMap.objects.filter(authorid=author)
        #print('--------------',author_obj)
        #author_names[author] = author_obj.user

    for r in range(rev_count['data']['revisions']):
        params = {'padID':padid,'rev':r+1}
        rev = call('getRevisionChangeset',params)
        ath = call('getRevisionAuthor',params)

        cs = changeset_parse(rev['data'])

        if (cs['final_op'] == '>'):
            addition[ath['data']] += cs['final_diff']
        if (cs['final_op'] == '<'):
            deletion[ath['data']] += cs['final_diff']

    call_response = {}
    author_count = len(author_names.keys())

    for i,v in enumerate(author_names.keys()):
        call_response[i] = {
            'authorid': v,
            'name':author_names[v],
            'addition':addition[v],
            'deletion':deletion[v],
        }

    #######################
    return Response(call_response)

def getGroupText(request,session_id,group_id):
    session = Session.objects.get(id=session_id)
    pad = Pad.objects.all().filter(session=session).filter(group=group_id)

    eth_group = SessionGroupMap.objects.all().filter(session=session)

    padid = pad[0].eth_padid

    res = call('getText',{'padID':padid})

    print('Get text:',res)

    read = call('getReadOnlyID',{'padID':padid})
    print('Get readonly',read)

    eth_session = request.session['ethsid']

    valid = int(datetime.datetime.today().timestamp() + 24 * 60 * 60)

    print(valid,' ',type(valid))

    auth_id = call('createAuthorIfNotExistsFor',{'authorMapper':request.user.id})
    print('Create author',auth_id)

    print('Group Id:---------------',eth_session)

    accessSession = call('createSession',{'groupID':eth_group[0].eth_groupid,'authorID':auth_id['data']['authorID'],'validUntil':valid})
    print('Access session',accessSession)

    return render(request,'session_main_padtext.html',{'padtext':res['data']['text'],'session_id':session_id,'session':session,'group_id':group_id,'pad_id':padid,'etherpad_url':settings.ETHERPAD_URL,'padname':read['data']['readOnlyID'],'sessionid':accessSession['data']['sessionID']})





def downloadLog(request,session_id):
    session = Session.objects.all().filter(id=session_id)
    if session.count() == 0:
        messages.error(request,'Specified session id is invalid')
        return redirect('project_home')
    else:
        session = Session.objects.get(id=session_id)
        # Preparing csv data File#####
        fname = session.name + '.csv'

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename="' + fname +'"'

        writer = csv.writer(response)
        writer.writerow(['timestamp','author','group','char_bank','source_length','operation','difference'])

        ##############################


        pad = Pad.objects.all().filter(session=session)


        for p in pad:

            padid =  p.eth_padid
            params = {'padID':padid}
            rev_count = call('getRevisionsCount',params)

            for r in range(rev_count['data']['revisions']):
                params = {'padID':pad[0].eth_padid,'rev':r+1}
                rev = call('getRevisionChangeset',params)
                ath = call('getRevisionAuthor',params)

                d = call('getRevisionDate',params)

                cs = changeset_parse(rev['data'])
                tp = int(d['data'])
                print(tp,type(tp))
                print(datetime.datetime.fromtimestamp(tp/1000).strftime('%H:%M:%S %d-%m-%Y'))
                print('   ',datetime.datetime.fromtimestamp(tp/1000).strftime('%H:%M:%S %d-%m-%Y'));
                writer.writerow([datetime.datetime.fromtimestamp(d["data"]/1000).strftime('%H:%M:%S %d-%m-%Y'),ath['data'],p.group,cs['bank'],cs['source_length'],cs['final_op'],cs['final_diff']])

            #print(datetime.datetime.utcfromtimestamp(d["data"]/1000).strftime('%Y-%m-%d %H:%M:%S'),',',pad.group,',',cs["bank"],',',cs["source_length"],',',cs["final_diff"],',',cs["final_op"],',',rev["data"],',',ath["data"])
    return response


def uploadAudio(request):
    if request.method == 'POST':
        form = AudioflForm(request.POST,request.FILES)
        print(form)
        if form.is_valid():
            print('Form is valid')
            newform = form.save(commit=False)
            djfile = File(request.FILES['data_blob'])
            newform.fl.save(request.FILES['data_blob'].name,djfile)
            newform.save()
            return HttpResponse('Done')
        else:
            print('Form not valid')
            return HttpResponse('Form not valid')
    else:

        return HttpResponse('Not done')



def uploadVad(request):
    if request.method == 'POST':
        form = VADForm(request.POST,request.FILES)
        print(form)
        if form.is_valid():
            print('Form is valid')
            session = form.cleaned_data.get("session")
            user = form.cleaned_data.get("user")
            group = form.cleaned_data.get("group")
            strDate = form.cleaned_data.get("strDate")
            milli = form.cleaned_data.get("milli")
            activity = form.cleaned_data.get("activity")

            strDate = (int)(float(strDate)/1000)

            dt = datetime.datetime.fromtimestamp(strDate)

            vad_object = VAD.objects.create(session=session,user=user,group=group,timestamp=dt,activity=activity)

            return HttpResponse('Done')
        else:
            print('Form not valid')
            return HttpResponse('Form not valid')
    else:

        return HttpResponse('Not done')



def LeaveSession(request):
    if 'joined' in request.session.keys():
        del request.session['joined']

    return redirect('student_entry')

def getPad(request,group_id):
    print('getPad:',request.session.keys())
    if 'joined' in request.session.keys():
        session_obj = SessionPin.objects.get(id=request.session['joined'])

        eth_session = request.session['ethsid']

        if int(group_id) > session_obj.session.groups or int(group_id) < 1:
            messages.error(request,'Invalid group id')
            return redirect('student_entry')


        pad = Pad.objects.get(session=session_obj.session,group=group_id)
        print(pad)
        print('Fetched-->',pad.eth_padid)

        padname = pad.eth_padid.split('$')

        form = AudioflForm()

        vad_form = VADForm()

        return render(request,'pad_audio_only.html',{'group':group_id,'session_obj':session_obj.session,'session':request.session['joined'],'form':form,'vad_form':vad_form,'etherpad_url':settings.ETHERPAD_URL,'padname':pad.eth_padid,'sessionid':eth_session})
    else:

        messages.error(request,'Session is not authenticated. Enter the access pin.')
        return redirect('student_entry')

def activateSession(request,session_id):
    session = Session.objects.all().filter(id=session_id)
    if session.count() == 0:
        messages.error(request,'Specified session id is invalid')
        return redirect('project_home')
    else:
        session = Session.objects.get(id=session_id)
        session.status = False
        session.save()
        messages.success(request,'Session is unarchived successfully.')
        return render(request,'dashboard.html',{'session':session,'filter':True})

def deactivateSession(request,session_id):
    session = Session.objects.all().filter(id=session_id)
    if session.count() == 0:
        messages.error(request,'Specified session id is invalid')
        return redirect('project_home')
    else:
        session = Session.objects.get(id=session_id)
        session.status = True
        session.save()
        messages.success(request,'Session is archived successfully.')
        return render(request,'dashboard.html',{'session':session,'filter':True})



def getSession(request,session_id):
    session = Session.objects.all().filter(id=session_id)
    if session.count() == 0:
        messages.error(request,'Specified session id is invalid')
        return redirect('project_home')
    else:
        session = Session.objects.get(id=session_id)

        session_group = SessionGroupMap.objects.get(session=session)



        eth_group = session_group.eth_groupid

        request.session['ethsid'] = eth_group

        print('Passing session id:',session)

        return render(request,'session_main.html',{'session':session,'eth_group':eth_group,'no_group':list(range(session.groups))})


class CompleteForm(SessionWizardView):
    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get_context_data(self, form, **kwargs):
        context = super(CompleteForm, self).get_context_data(form=form, **kwargs)
        if self.steps.current == 'overview':
            context.update({'all_data': self.get_all_cleaned_data()})
        return context


    @transaction.atomic
    def done(self, form_list, **kwargs):
        print('done called')
        all_data = self.get_all_cleaned_data()
        print(all_data)
        current_user = self.request.user
        project = Project.objects.create(user=current_user,questionnaire_type=all_data['type_questionnaire'],project_name=all_data['project_name'],project_type=all_data['project_type'],test_project=all_data['test_project'],project_status=all_data['project_status'])
        survey = Survey.objects.create(project=project,start_date = all_data['start_date'],end_date=all_data['end_date'],survey_name = all_data['name_of_survey'],product_name=all_data['product_name'],product_type=all_data['project_type'],product_industry=all_data['product_industry'], title=all_data['title'],subtitle=all_data['subtitle'],paragraph=all_data['paragraph'])

        for i in range(int(all_data['project_type'])):
            survey_url = Link.objects.create(survey=survey,sequence=(i+1))


        messages.success(self.request, 'Project created successfully !')
        return redirect('project_home')
