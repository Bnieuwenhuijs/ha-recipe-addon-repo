ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Alle modules ineens, zodat een nieuwe module niet vergeten kan worden.
COPY *.py ./
COPY templates/ templates/
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
