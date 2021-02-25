from .models import Character
from example.celery import app


@app.task()
def reveal_alignment(cid):
    char = Character.objects.get(pk=cid)
    print(char.alignment or "Unaligned")
