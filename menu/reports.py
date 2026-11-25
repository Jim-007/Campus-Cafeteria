"""Sales report for the owner (FR12)."""
import csv
from datetime import timedelta

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import ExtractHour
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from orders.models import Order, OrderItem, Payment

RANGES = {'1': 'Today', '7': 'Last 7 days', '30': 'Last 30 days'}


def _since(days):
    """Start of the report period (midnight today minus days-1)."""
    midnight = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - timedelta(days=days - 1)


@role_required('is_owner')
def report(request):
    """Show totals, top items, peak hours and payment split; optionally export CSV."""
    days = request.GET.get('days', '1')
    if days not in RANGES:
        days = '1'
    since = _since(int(days))

    orders = Order.objects.filter(created_at__gte=since)
    valid = orders.exclude(status=Order.CANCELLED)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order', 'Date', 'Customer', 'Status', 'Payment', 'Total (BDT)'])
        for order in orders.select_related('user', 'payment').prefetch_related('lines'):
            writer.writerow([
                order.pk, timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M'),
                order.user.username, order.get_status_display(),
                order.payment.get_method_display(), order.total,
            ])
        return response

    line_total = ExpressionWrapper(F('quantity') * F('unit_price'), output_field=DecimalField())
    revenue = OrderItem.objects.filter(order__in=valid).aggregate(t=Sum(line_total))['t'] or 0
    top_items = (OrderItem.objects.filter(order__in=valid)
                 .values('item__name').annotate(qty=Sum('quantity'), money=Sum(line_total))
                 .order_by('-qty')[:5])
    peak = (valid.annotate(hour=ExtractHour('created_at'))
            .values('hour').annotate(n=Count('id')).order_by('-n', 'hour')[:5])
    pay_split = (Payment.objects.filter(order__in=valid)
                 .values('method').annotate(n=Count('id'), money=Sum('amount')).order_by('-money'))
    method_names = dict(Payment.METHODS)
    split = [{'name': method_names[p['method']], 'n': p['n'], 'money': p['money']} for p in pay_split]
    max_qty = max([t['qty'] for t in top_items], default=1)
    top = [dict(t, width=int(100 * t['qty'] / max_qty)) for t in top_items]

    context = {
        'ranges': RANGES, 'days': days, 'order_count': valid.count(),
        'cancelled_count': orders.filter(status=Order.CANCELLED).count(),
        'revenue': revenue, 'top_items': top, 'peak_hours': list(peak), 'pay_split': split,
    }
    return render(request, 'reports/report.html', context)
