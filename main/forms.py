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


#CONSUMER PROFILE
class ConsumerProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150)

    phone_number = forms.CharField(
        label="Nomor Telepon (+62)",
        required=False,
        help_text="Masukkan nomor setelah +62, contoh: 81234567890.",
        widget=forms.TextInput(
            attrs={
                "placeholder": "81234567890",
                "inputmode": "numeric",
            }
        ),
    )

    class Meta:
        model = ConsumerProfile
        fields = ["phone_number"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields["username"].initial = self.user.username

        # tampilkan nomor tanpa +62 agar pengguna hanya
        
        # mengisi bagian nomor setelah kode negara
        if not self.is_bound and self.instance.phone_number:
            phone = self.instance.phone_number
            if phone.startswith("+62"):
                phone = phone[3:]
            elif phone.startswith("62"):
                phone = phone[2:]
            elif phone.startswith("0"):
                phone = phone[1:]

            self.fields["phone_number"].initial = phone

    def clean_username(self):
        username = self.cleaned_data["username"]

        if (
            User.objects.filter(username=username)
            .exclude(pk=self.user.pk)
            .exists()
        ):
            raise forms.ValidationError("Username sudah digunakan.")

        return username

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"].strip()

        if not phone:
            return ""

        # izinkan pengguna menulis spasi ato tanda hubung
        phone = phone.replace(" ", "").replace("-", "")

        # terima juga format +62 ato 0 jika diketik manual
        if phone.startswith("+62"):
            phone = phone[3:]
        elif phone.startswith("62"):
            phone = phone[2:]
        elif phone.startswith("0"):
            phone = phone[1:]

        if not phone.isdigit():
            raise forms.ValidationError(
                "Nomor telepon hanya boleh berisi angka."
            )

        if not 9 <= len(phone) <= 13:
            raise forms.ValidationError(
                "Nomor setelah +62 harus terdiri dari 9–13 digit."
            )

        return f"+62{phone}"

    def save(self, commit=True):
        profile = super().save(commit=False)

        if self.user:
            self.user.username = self.cleaned_data["username"]

            if commit:
                self.user.save()
                profile.user = self.user
                profile.save()

        return profile