# extest
For using you need to start Redis-server, and have postgresql database, db_name = extextdb, name/pass = postgres/postgres.
***
You dont specify Python version in task, so I have to used Python 3.6.
***
You need next modules:
* --pre xhtml2pdf
* celery
* django
* BeautifulSoup4
* requests
***
Dont forget about migrations. Celery start with:
* celery -A extext.longjobs worker --loglevel=info

