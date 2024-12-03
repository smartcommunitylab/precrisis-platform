FROM python:3.10.4
WORKDIR /app
RUN pip3 install vidgear Flask seaborn aioflask flask-login oauthlib python-dotenv
COPY app.py /app/
COPY templates/ /app/templates/

COPY env /app/env
ENTRYPOINT [ "python3" ]
CMD [ "app.py" ]