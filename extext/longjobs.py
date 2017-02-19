import requests
import os

from datetime import timedelta
from bs4 import BeautifulSoup
from xhtml2pdf import pisa

from celery import Celery, group, chord
from celery.result import allow_join_result

from django.utils import timezone
from django.core.mail import EmailMessage


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extext.settings')
import django
django.setup()  # T_T
from .models import NewsInstance
app = Celery('extext.longjobs', broker='redis://localhost:6379/0')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


news_html_present = """
    <div>
        <h3><b>{title}</b></h3>
        <p><span style="color: red;">{time}</span> {date} - <span style="color:red;">{category}</span></p>
        <p>{description}</p>
    </div>
"""

tuple_category_content = (
    ("russia", "Россия"),
    ("world", "Мир"),
    ("ussr", "Бывший СССР"),
    ("economics", "Финансы"),
    ("business", "Бизнес"),
    ("forces", "Силовые структуры"),
    ("science", "Наука и техника"),
    ("sport", "Спорт"),
    ("culture", "Культура"),
    ("media", "Интернет и СМИ"),
    ("style", "Ценности"),
    ("travel", "Путешествия"),
    ("life", "Из жизни"),
    ("motor", "Мотор"),
    ("realty", "Недвижимость"),
)

std_en_category_set = frozenset(a for a,b in tuple_category_content)

category_ru_to_en = {b:a for a,b in tuple_category_content}
category_en_to_ru = dict(tuple_category_content)

@app.task
def refresh_rss_request(category=''):
    try:
        response = requests.get("https://lenta.ru/rss/news{category}/".format(category=category))
        if not (200 <= response.status_code < 300):
            result = 'lenta.ru rss connection error'
        soup = BeautifulSoup(response.text, 'html.parser')  # lxml do not parse <![CDATA[%s]]> objects
        targets = soup.findAll("item")
        # result = [
        #     NewsInstance(
        #         title=i.title.text,
        #         description=i.description.text.strip(),
        #         time=timezone.datetime.strptime(i.pubdate.text,'%a, %d %b %Y %H:%M:%S %z'),
        #         category=category_ru_to_en[i.category.text],
        #     )
        #     for i in soup.findAll("item")
        #     if not NewsInstance.objects.filter(
        #             title=i.title.text,
        #             description=i.description.text.strip(),
        #             time=timezone.datetime.strptime(i.pubdate.text,'%a, %d %b %Y %H:%M:%S %z'),
        #             category=category_ru_to_en[i.category.text],
        #         ).exists()
        # ]
        for item in soup.findAll("item"):
            title = item.title.text
            description = item.description.text.strip()
            time = timezone.datetime.strptime(item.pubdate.text,'%a, %d %b %Y %H:%M:%S %z')
            category = category_ru_to_en[item.category.text]
            NewsInstance.objects.get_or_create(title=title, description=description, time=time, category=category)  # what more efficient - get_or_create for each one or filter exists then bulk_create? second option causes race condition.
    except Exception as e:
        print("EXCEPTION %s" % e)
        # os.system('echo "%s app.task refrsh" >> errors.log' % e)
        pass
    finally:
        return True

@app.task
def periodic_task(depth=0):
    if not depth:
        group_of_tasks = group(refresh_rss_request.s(category=category) for category in std_en_category_set).apply_async()
    main_task = refresh_rss_request.apply_async()
    return periodic_task.apply_async(kwargs={"depth":depth+1},countdown=120.0)

@app.task
def extend_database(start_date, end_date, categories, email):
    # return chord(
    #     refresh_rss_request.s(category=category) for category in categories
    # )(crate_html_file.s(start_date, end_date, categories, email))
    return refresh_rss_request.apply_async(link=crate_html_file.s(start_date, end_date, categories, email))

@app.task
def crate_html_file(_, start_date, end_date, categories, email):
    fdate_start = timezone.datetime.date(timezone.datetime.strptime(start_date,'%Y-%m-%dT%H:%M:%S'))  # WE NEED TO GET DAY, MONTH, YEAR  # 2017-02-12T00:00:00 #.date(start_date) 
    fdate_end = timezone.datetime.date(timezone.datetime.strptime(end_date,'%Y-%m-%dT%H:%M:%S')) + timedelta(days=1)  #.date(end_date)
    query_string = NewsInstance.objects.filter(time__gte=fdate_start,time__lt=fdate_end)
    if '' not in categories:
        query_string = query_string.filter(category__in=categories)
    query_string = query_string.order_by('-time')
    html_content = '<br>'.join(
        news_html_present.format(
            title=news_obj.title,
            time=news_obj.time.strftime("%H:%M"),
            date=news_obj.time.strftime("%d %b %y"),
            category=category_en_to_ru[news_obj.category],
            description=news_obj.description,

        )
        for news_obj in query_string.all()
    )
    if not html_content:
        html_content = '''
        <html>
            <head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
                <style type="text/css">
                    @page { size: A4; margin: 1cm; }
                    @font-face { font-family: Roboto; src: "http://127.0.0.1:8000/static/fonts/roboto/Roboto-Regular.ttf"; }
                    b { font-family: Roboto; }
                    p { font-family: Roboto; }
                </style>
            </head>
            <body>
                <h1>We dont have news for you</h1>
                <p>Sorry ;(</p>
            </body>
        </html>'''
    else:
        html_content = '''
        <html>
            <head>
                <meta http-equiv="content-type" content="text/html; charset=UTF-8"/>
                <style type="text/css">
                    @page { size: A4; margin: 1cm; }
                    @font-face { font-family: Roboto; src: "http://127.0.0.1:8000/static/fonts/roboto/Roboto-Regular.ttf"; }
                    b { font-family: Roboto; }
                    p { font-family: Roboto; }
                </style>
            </head>
            <body>
                <h1>News specially for %s</h1><br>''' % email + html_content + '</body></html>'
    html_path = os.path.dirname(__file__) + "/pdfs/%s.html" % email
    with open(html_path,"wb") as fp:
        fp.write(bytes(html_content.encode('UTF-8')))
    return create_pdf.delay(html_path, email)

@app.task
def create_pdf(html_path, email):
    path_to_pdf = html_path[:-4] + "pdf"
    with open(html_path,'r') as fphtml, open(path_to_pdf,'w+b') as fpdf:
        pisa.CreatePDF(fphtml.read(), dest=fpdf, encoding='UTF-8') #  .encode('UTF-8') , encoding='UTF-8'  # str(, encoding='UTF-8')
    os.remove(html_path)
    return send_pdf_mail.delay(path_to_pdf, email)
    
@app.task
def send_pdf_mail(path_to_pdf, email):
    message = EmailMessage(
        subject='YOUR ORDER',
        body='You have to order this pdf file with digest from lenta.ru',
        from_email='lentaslave@mail.ru',
        to=[email],
    ) # pass IhAtEsMtP
    message.attach_file(path_to_pdf)
    message.send(fail_silently=True)
    os.remove(path_to_pdf)
    return

# @app.task
# def extend_database(start_date, end_date, categories, email):
#     today = timezone.datetime.today(datetime.now) # WE NEED TO GET DAY, MONTH, YEAR
#     tmp_datetime = start_date.copy()
#     total_result = []
#     while tmp_datetime <= end_date:
#         total_result.append(['<h2>Date: %s</h2><br>'%tmp_datetime])
#         for category in categories:
#             try:
#                 html_obj = CategoryDay.objects.filter(category=category, time=tmp_datetime)
#                 if html_obj and html_obj.status == 1:
#                     result = html_obj.rss_news
#                 else:
#                     response = requests.get("https://lenta.ru{category}/{date}/".format(category=category,date=tmp_datetime.strftime("%Y/%m/%d")), headers=sp_headers)
#                     if not (200 <= response.status_code < 300):
#                         result = 'lenta.ru do not have content for %s' % tmp_datetime.strftime("%d %M %Y")
#                     soup = BeautifulSoup(response.text, 'html.parser')
#                     targets = soup.findAll("section", {"class" : "b-longgrid-column"})  # b-layout_archive
#                     result = '<br><br>'.join(item.prettify() for column in targets for item in column.findAll("div", { "class" : "item" }))
#             except:
#                 result = ''
#             else:
#                 try:
#                     status = int(tmp_datetime != today)
#                     if html_obj:
#                         if html_obj.status == 0:
#                             html_obj.status = status
#                             html_obj.rss_news = result
#                             html_obj.save()
#                     else:
#                         html_obj = CategoryDay(category=category, time=tmp_datetime, status=status, rss_news=result)
#                         html_obj.save()
#                 except Exception as e:
#                     os.system('echo "%s" >> errors.log' % e)
#             finally:
#                 if result:
#                 total_result[-1].append("<h3>%s</h3>%s" % (category,result))
#         tmp_datetime += timedelta(days=1)
#         total_result[-1] = '<br><br>'.join(total_result[-1])
#     total_result = '<br>'.append(total_result)
#     create_pdf.delay(total_result, email)
#     return
