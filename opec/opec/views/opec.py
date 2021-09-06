from django.shortcuts import redirect, render
from django.views.generic import TemplateView


class SignUpView(TemplateView):
    template_name = 'registration/signup.html'


def home(request):
    if request.user.is_authenticated:
        if request.user.is_evaluator:
            return redirect('evaluators:exam_change_list')
        else:
            return redirect('competitors:exam_list')
    return render(request, 'opec/Home.html')



def exams(request):
    return render(request, 'opec/Exams.html')

def contact(request):
    return render(request, 'opec/Contact.html')
