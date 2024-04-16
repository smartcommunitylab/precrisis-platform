FROM python:3.10.4
WORKDIR /app
RUN pip3 install vidgear Flask seaborn aioflask flask-login oauthlib
COPY app.py /app/
ENTRYPOINT [ "python3" ]
CMD [ "app.py" ]