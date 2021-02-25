from django.db import models


class Alignment(models.Model):
    class LawVsChaos(models.TextChoices):
        LAWFUL = "Lawful"
        NEUTRAL = "Neutral"
        CHAOTIC = "Chaotic"

    class GoodVsEvil(models.TextChoices):
        GOOD = "Good"
        NEUTRAL = "Neutral"
        EVIL = "Evil"

    law_vs_chaos = models.CharField(
        max_length=7, choices=LawVsChaos.choices, default=LawVsChaos.NEUTRAL
    )
    good_vs_evil = models.CharField(
        max_length=7, choices=GoodVsEvil.choices, default=GoodVsEvil.NEUTRAL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["law_vs_chaos", "good_vs_evil"],
                name="unique_alignment",
            )
        ]

    def __str__(self):
        return f"{self.law_vs_chaos} {self.good_vs_evil}"


class Character(models.Model):
    name = models.CharField(max_length=50)
    alignment = models.ForeignKey(
        Alignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="characters",
    )

    def __str__(self):
        return self.name
