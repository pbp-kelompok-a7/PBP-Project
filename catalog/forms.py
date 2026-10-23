from django import forms

from catalog.models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]

    def clean_comment(self):
        # buang spasi di awal/akhir, terus cek minimal 5 huruf biar ga asal isi
        comment = self.cleaned_data["comment"].strip()
        if len(comment) < 5:
            raise forms.ValidationError("Comment must be at least 5 characters.")
        return comment