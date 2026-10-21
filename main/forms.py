from django import forms
from .models import MerchantProduct
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from .models import ConsumerProfile


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


#ConsumerProfile
class ConsumerProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150)

    class Meta:
        model = ConsumerProfile
        fields = ["phone_number"]
        labels = {
            "phone_number": "Nomor Telepon",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields["username"].initial = self.user.username

    def clean_username(self):
        username = self.cleaned_data["username"]

        if User.objects.filter(username=username).exclude(
            pk=self.user.pk
        ).exists():
            raise forms.ValidationError("Username sudah digunakan.")

        return username

    def save(self, commit=True):
        profile = super().save(commit=False)

        if self.user:
            self.user.username = self.cleaned_data["username"]

            if commit:
                self.user.save()
                profile.user = self.user
                profile.save()

        return profile

