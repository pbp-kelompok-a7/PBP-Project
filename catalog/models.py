from django.contrib.auth.models import User
from django.db import models


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="catalog_reviews")
    # SEMENTARA: pake id paket dummy dulu
    # nanti diganti: inventory = models.ForeignKey(MerchantInventory, ...)
    # sama ditambah: order = models.OneToOneField(Order, ...) kalau model rafael udah ada
    inventory_id = models.PositiveIntegerField()
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        # 1 user cuma boleh review 1 paket sekali
        constraints = [
            models.UniqueConstraint(fields=["user", "inventory_id"], name="unique_review_per_paket")
        ]

    def __str__(self):
        return f"{self.user.username} - paket {self.inventory_id} ({self.rating}/5)"