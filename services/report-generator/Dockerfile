FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY report-generator/requirements.txt .
RUN pip install -r requirements.txt --target .

COPY shared/models.py .
COPY report-generator/handler.py .

CMD ["handler.handler"]
