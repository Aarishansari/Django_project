from django.urls import include, path

from .views import opec, competitors, evaluators

urlpatterns = [
    path('', opec.home, name='home'),
    path('exams/', opec.exams, name='exams'),
    path('contact/', opec.contact, name='contact'),

    path('competitors/', include(([
        path('', competitors.ExamListView.as_view(), name='exam_list'),
        path('interests/', competitors.CompetitorInterestsView.as_view(), name='competitor_interests'),
        path('taken/', competitors.TakenExamListView.as_view(), name='taken_exam_list'),
        path('exam/<int:pk>/', competitors.take_exam, name='take_exam'),
    ], 'opec'), namespace='competitors')),

    path('evaluators/', include(([
        path('', evaluators.ExamListView.as_view(), name='exam_change_list'),
        path('exam/add/', evaluators.ExamCreateView.as_view(), name='exam_add'),
        path('exam/<int:pk>/', evaluators.ExamUpdateView.as_view(), name='exam_change'),
        path('exam/<int:pk>/delete/', evaluators.ExamDeleteView.as_view(), name='exam_delete'),
        path('exam/<int:pk>/results/', evaluators.ExamResultsView.as_view(), name='exam_results'),
        path('exam/<int:pk>/question/add/', evaluators.question_add, name='question_add'),
        path('exam/<int:exam_pk>/question/<int:question_pk>/', evaluators.question_change, name='question_change'),
        path('exam/<int:exam_pk>/question/<int:question_pk>/delete/', evaluators.QuestionDeleteView.as_view(), name='question_delete'),
    ], 'opec'), namespace='evaluators')),
]
