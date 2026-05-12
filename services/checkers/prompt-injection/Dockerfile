FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY checkers/prompt-injection/requirements.txt .
RUN pip install -r requirements.txt --target .

COPY shared/models.py .
COPY checkers/prompt-injection/handler.py .

CMD ["handler.handler"]
