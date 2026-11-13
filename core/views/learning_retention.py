from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.shortcuts import render
from django.utils.translation import gettext as _
from core.views.admin import staff_or_admin_role_required
from core.models import LearningEvent, PointTransaction, QuickLessonMatch, QuickLessonRequest
from core.services.lesson_lifecycle import completed_lessons


@login_required
@staff_or_admin_role_required
@never_cache
def learning_retention(request):
    # Only actual two-point signup cohorts; do not reinterpret legacy bonuses.
    eligible = set(PointTransaction.objects.filter(transaction_type='signup_bonus', amount=2).values_list('user_id',flat=True))
    histories = defaultdict(list)
    completed = completed_lessons().filter(request__purpose='lesson').distinct()
    for uid, ended in completed.filter(request__student__user_id__in=eligible).order_by('end_at').values_list('request__student__user_id','end_at'):
        histories[uid].append(ended)
    cohort = {uid: ends[1] for uid,ends in histories.items() if len(ends)>=2}
    viewed = {uid for uid,at in LearningEvent.objects.filter(kind='purchase_view_after_two').values_list('user_id','created_at') if uid in cohort and at>=cohort[uid]}
    bought = {uid for uid,at in PointTransaction.objects.filter(transaction_type='purchase',amount__gt=0,user_id__in=cohort).values_list('user_id','created_at') if at>=cohort[uid]}
    third = sum(len(histories[uid])>=3 for uid in cohort)
    attempts = QuickLessonMatch.objects.filter(request__student__user_id__in=cohort, request__purpose='lesson')
    from django.utils import timezone
    from datetime import timedelta
    unresolved = attempts.exclude(pk__in=completed.values('pk')).filter(request__created_at__lt=timezone.now()-timedelta(minutes=10)).count()
    waiting = QuickLessonRequest.objects.filter(student__user_id__in=cohort,purpose='lesson',status='cancelled',quicklessonmatch__isnull=True).count()
    rows=[(_('Completed at least two lessons'),len(cohort)),(_('Opened point purchase after lesson two'),len(viewed)),(_('Purchased points after lesson two'),len(bought)),(_('Completed a third lesson'),third),(_('Other ended or old connection attempts (not completed lessons)'),unresolved),(_('Cancelled requests without a match'),waiting)]
    return render(request,'core/learning_retention.html',{'rows':rows})
