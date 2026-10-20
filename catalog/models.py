from django.contrib.auth.models import User
from django.db import models

from main.models import MerchantProduct, OrderSystem


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="catalog_reviews")
    # 1 order cuma boleh direview sekali, makanya pake OneToOne
    order = models.OneToOneField(OrderSystem, on_delete=models.CASCADE, related_name="review")
    product = models.ForeignKey(MerchantProduct, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.product.product_name} ({self.rating}/5)"