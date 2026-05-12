FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY checkers/excessive-agency/requirements.txt .
RUN pip install -r requirements.txt --target .

COPY shared/models.py .
COPY checkers/excessive-agency/handler.py .

CMD ["handler.handler"]
