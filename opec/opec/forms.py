from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.forms.utils import ValidationError

from opec.models import (Answer, Question, Competitor, CompetitorAnswer, Subject, User, Registration)


class EvaluatorSignUpForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.IntegerField()
    university = forms.CharField(max_length=200)
    university_id = forms.CharField(max_length=200)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username","email","phone","university","university_id","password1","password2"]
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_evaluator = True
        if commit:
            user.save()
        return user


class CompetitorSignUpForm(UserCreationForm):
    email = forms.EmailField()
    phone = forms.IntegerField()
    university = forms.CharField(max_length=200)
    university_id = forms.CharField(max_length=200)
    interests = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username","email","phone","university","university_id","password1","password2","interests"]
    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_competitor = True
        user.save()
        competitor = Competitor.objects.create(user=user)
        competitor.interests.add(*self.cleaned_data.get('interests'))
        return user


class CompetitorInterestsForm(forms.ModelForm):
    class Meta:
        model = Competitor
        fields = ('interests', )
        widgets = {
            'interests': forms.CheckboxSelectMultiple
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('text', )


class BaseAnswerInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        has_one_correct_answer = False
        for form in self.forms:
            if not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('is_correct', False):
                    has_one_correct_answer = True
                    break
        if not has_one_correct_answer:
            raise ValidationError('Mark at least one answer as correct.', code='no_correct_answer')


class TakeExamForm(forms.ModelForm):
    answer = forms.ModelChoiceField(
        queryset=Answer.objects.none(),
        widget=forms.RadioSelect(),
        required=True,
        empty_label=None)

    class Meta:
        model = CompetitorAnswer
        fields = ('answer', )

    def __init__(self, *args, **kwargs):
        question = kwargs.pop('question')
        super().__init__(*args, **kwargs)
        self.fields['answer'].queryset = question.answers.order_by('text')
