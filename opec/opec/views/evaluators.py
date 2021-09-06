from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from ..decorators import evaluator_required
from ..forms import BaseAnswerInlineFormSet, QuestionForm, EvaluatorSignUpForm
from ..models import Answer, Question, Exam, User


class EvaluatorSignUpView(CreateView):
    model = User
    form_class = EvaluatorSignUpForm
    template_name = 'registration/signup_form.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'evaluator'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('evaluators:exam_change_list')


@method_decorator([login_required, evaluator_required], name='dispatch')
class ExamListView(ListView):
    model = Exam
    ordering = ('name', )
    context_object_name = 'exams'
    template_name = 'opec/evaluators/exam_change_list.html'

    def get_queryset(self):
        queryset = self.request.user.exams \
            .select_related('subject') \
            .annotate(questions_count=Count('questions', distinct=True)) \
            .annotate(taken_count=Count('taken_exams', distinct=True))
        return queryset


@method_decorator([login_required, evaluator_required], name='dispatch')
class ExamCreateView(CreateView):
    model = Exam
    fields = ('name', 'subject', )
    template_name = 'opec/evaluators/exam_add_form.html'

    def form_valid(self, form):
        exam = form.save(commit=False)
        exam.owner = self.request.user
        exam.save()
        messages.success(self.request, 'The exam was created with success! Go ahead and add some questions now.')
        return redirect('evaluators:exam_change', exam.pk)


@method_decorator([login_required, evaluator_required], name='dispatch')
class ExamUpdateView(UpdateView):
    model = Exam
    fields = ('name', 'subject', )
    context_object_name = 'exam'
    template_name = 'opec/evaluators/exam_change_form.html'

    def get_context_data(self, **kwargs):
        kwargs['questions'] = self.get_object().questions.annotate(answers_count=Count('answers'))
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        '''
        This method is an implicit object-level permission management
        This view will only match the ids of existing exams that belongs
        to the logged in user.
        '''
        return self.request.user.exams.all()

    def get_success_url(self):
        return reverse('evaluators:exam_change', kwargs={'pk': self.object.pk})


@method_decorator([login_required, evaluator_required], name='dispatch')
class ExamDeleteView(DeleteView):
    model = Exam
    context_object_name = 'exam'
    template_name = 'opec/evaluators/exam_delete_confirm.html'
    success_url = reverse_lazy('evaluators:exam_change_list')

    def delete(self, request, *args, **kwargs):
        exam = self.get_object()
        messages.success(request, 'The exam %s was deleted with success!' % exam.name)
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return self.request.user.exams.all()


@method_decorator([login_required, evaluator_required], name='dispatch')
class ExamResultsView(DetailView):
    model = Exam
    context_object_name = 'exam'
    template_name = 'opec/evaluators/exam_results.html'

    def get_context_data(self, **kwargs):
        exam = self.get_object()
        taken_exams = exam.taken_exams.select_related('competitor__user').order_by('-date')
        total_taken_exams = taken_exams.count()
        exam_score = exam.taken_exams.aggregate(average_score=Avg('score'))
        extra_context = {
            'taken_exams': taken_exams,
            'total_taken_exams': total_taken_exams,
            'exam_score': exam_score
        }
        kwargs.update(extra_context)
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        return self.request.user.exams.all()


@login_required
@evaluator_required
def question_add(request, pk):
    # By filtering the exam by the url keyword argument `pk` and
    # by the owner, which is the logged in user, we are protecting
    # this view at the object-level. Meaning only the owner of
    # exam will be able to add questions to it.
    exam = get_object_or_404(Exam, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()
            messages.success(request, 'You may now add answers/options to the question.')
            return redirect('evaluators:question_change', exam.pk, question.pk)
    else:
        form = QuestionForm()

    return render(request, 'opec/evaluators/question_add_form.html', {'exam': exam, 'form': form})


@login_required
@evaluator_required
def question_change(request, exam_pk, question_pk):
    # Simlar to the `question_add` view, this view is also managing
    # the permissions at object-level. By querying both `exam` and
    # `question` we are making sure only the owner of the exam can
    # change its details and also only questions that belongs to this
    # specific exam can be changed via this url (in cases where the
    # user might have forged/player with the url params.
    exam = get_object_or_404(Exam, pk=exam_pk, owner=request.user)
    question = get_object_or_404(Question, pk=question_pk, exam=exam)

    AnswerFormSet = inlineformset_factory(
        Question,  # parent model
        Answer,  # base model
        formset=BaseAnswerInlineFormSet,
        fields=('text', 'is_correct'),
        min_num=2,
        validate_min=True,
        max_num=10,
        validate_max=True
    )

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        formset = AnswerFormSet(request.POST, instance=question)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, 'Question and answers saved with success!')
            return redirect('evaluators:exam_change', exam.pk)
    else:
        form = QuestionForm(instance=question)
        formset = AnswerFormSet(instance=question)

    return render(request, 'opec/evaluators/question_change_form.html', {
        'exam': exam,
        'question': question,
        'form': form,
        'formset': formset
    })


@method_decorator([login_required, evaluator_required], name='dispatch')
class QuestionDeleteView(DeleteView):
    model = Question
    context_object_name = 'question'
    template_name = 'opec/evaluators/question_delete_confirm.html'
    pk_url_kwarg = 'question_pk'

    def get_context_data(self, **kwargs):
        question = self.get_object()
        kwargs['exam'] = question.exam
        return super().get_context_data(**kwargs)

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        messages.success(request, 'The question %s was deleted with success!' % question.text)
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return Question.objects.filter(exam__owner=self.request.user)

    def get_success_url(self):
        question = self.get_object()
        return reverse('evaluators:exam_change', kwargs={'pk': question.exam_id})
