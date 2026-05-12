FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY requirements.txt .
RUN pip install -r requirements.txt --target .

COPY ../shared/models.py .
COPY handler.py .

CMD ["handler.handler"]
