FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY checkers/sensitive-disclosure/requirements.txt .
RUN pip install -r requirements.txt --target .

COPY shared/models.py .
COPY checkers/sensitive-disclosure/handler.py .

CMD ["handler.handler"]
