from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import OrderLine


class Command(BaseCommand):
    help = 'Update old Orderlines to use the new total_cost field. The field' \
           ' will tak the current cost value and the cost value will become' \
           ' the base price of what the orderline is targeting.' \
           'After that, cost will be the base cost, impacted by coupon' \
           ' and total_cost will be base cost plus options.'

    def handle(self, *args, **options):
        with transaction.atomic():
            order_lines = OrderLine.objects.all()
            print(f'{order_lines.count()} order lines to process.')
            for line in order_lines:
                print(f'Processing order line {line.id} . . .')
                print(f'Current cost: {line.cost}')
                line.total_cost = line.cost
                base = line.content_object
                base_price = base.price if base.price else 0
                print(f'Base object: {base.id} {base.name} {base_price}')
                line.cost = base_price - line.coupon_real_value
                # No need to apply coupon on total_cost for it copies old cost
                print(f'New cost: '
                      f'{base_price} - {line.coupon_real_value} = {line.cost}')
                print('= = = = = = = = = = = = = = = = = = = = = =')
