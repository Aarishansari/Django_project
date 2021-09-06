from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from ..decorators import competitor_required
from ..forms import CompetitorInterestsForm, CompetitorSignUpForm, TakeExamForm
from ..models import Exam, Competitor, TakenExam, User


class CompetitorSignUpView(CreateView):
    model = User
    form_class = CompetitorSignUpForm
    template_name = 'registration/signup_form.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'competitor'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('competitors:exam_list')


@method_decorator([login_required, competitor_required], name='dispatch')
class CompetitorInterestsView(UpdateView):
    model = Competitor
    form_class = CompetitorInterestsForm
    template_name = 'opec/competitors/interests_form.html'
    success_url = reverse_lazy('competitors:exam_list')

    def get_object(self):
        return self.request.user.competitor

    def form_valid(self, form):
        messages.success(self.request, 'Interests updated with success!')
        return super().form_valid(form)


@method_decorator([login_required, competitor_required], name='dispatch')
class ExamListView(ListView):
    model = Exam
    ordering = ('name', )
    context_object_name = 'exams'
    template_name = 'opec/competitors/exam_list.html'

    def get_queryset(self):
        competitor = self.request.user.competitor
        competitor_interests = competitor.interests.values_list('pk', flat=True)
        taken_exams = competitor.exams.values_list('pk', flat=True)
        queryset = Exam.objects.filter(subject__in=competitor_interests) \
            .exclude(pk__in=taken_exams) \
            .annotate(questions_count=Count('questions')) \
            .filter(questions_count__gt=0)
        return queryset


@method_decorator([login_required, competitor_required], name='dispatch')
class TakenExamListView(ListView):
    model = TakenExam
    context_object_name = 'taken_exams'
    template_name = 'opec/competitors/taken_exam_list.html'

    def get_queryset(self):
        queryset = self.request.user.competitor.taken_exams \
            .select_related('exam', 'exam__subject') \
            .order_by('exam__name')
        return queryset


@login_required
@competitor_required
def take_exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    competitor = request.user.competitor

    if competitor.exams.filter(pk=pk).exists():
        return render(request, 'competitors/taken_exam.html')

    total_questions = exam.questions.count()
    unanswered_questions = competitor.get_unanswered_questions(exam)
    total_unanswered_questions = unanswered_questions.count()
    progress = 100 - round(((total_unanswered_questions - 1) / total_questions) * 100)
    question = unanswered_questions.first()

    if request.method == 'POST':
        form = TakeExamForm(question=question, data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                competitor_answer = form.save(commit=False)
                competitor_answer.competitor = competitor
                competitor_answer.save()
                if competitor.get_unanswered_questions(exam).exists():
                    return redirect('competitors:take_exam', pk)
                else:
                    correct_answers = competitor.exam_answers.filter(answer__question__exam=exam, answer__is_correct=True).count()
                    score = round((correct_answers / total_questions) * 100.0, 2)
                    TakenExam.objects.create(competitor=competitor, exam=exam, score=score)
                    if score < 50.0:
                        messages.warning(request, 'Better luck next time! Your score for the exam %s was %s.' % (exam.name, score))
                    else:
                        messages.success(request, 'Congratulations! You completed the exam %s with success! You scored %s points.' % (exam.name, score))
                    return redirect('competitors:exam_list')
    else:
        form = TakeExamForm(question=question)

    return render(request, 'opec/competitors/take_exam_form.html', {
        'exam': exam,
        'question': question,
        'form': form,
        'progress': progress
    })
