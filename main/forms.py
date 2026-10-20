from django import forms
from .models import MerchantProduct


class MerchantProductForm(forms.ModelForm):
    class Meta:
        model = MerchantProduct
        fields = [
            "product_name",
            "product_stock",
            "product_status",
            "real_price",
            "discount_rate",
            "start_pickup",
            "end_pickup",
        ]
        widgets = {
            "start_pickup": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "end_pickup": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "discount_rate": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01", "placeholder": "Enter a percentage from 0 to 100"}),
        }
        labels = {
            "discount_rate": "Discount rate (%)",
        }

    def clean(self):
        cleaned_data = super().clean()
        start_pickup = cleaned_data.get("start_pickup")
        end_pickup = cleaned_data.get("end_pickup")

        if start_pickup and end_pickup and end_pickup <= start_pickup:
            self.add_error("end_pickup", "Waktu selesai pickup harus setelah waktu mulai pickup.")

        return cleaned_data
