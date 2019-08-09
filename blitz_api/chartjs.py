import string

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet, Sum, Count
from django.db.models.functions import TruncMonth, TruncDay, \
    TruncWeek, TruncYear
from django.http import HttpRequest
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.template.defaultfilters import date


class ChartJSMixin(object):
    date_field: string = None
    quantity_field: string = None

    INTERVAL = 'interval'
    AGGREGATE = 'aggregate'
    END = 'end'
    START = 'start'
    GROUP_BY_OBJECT = 'group_by_object'  # object_id or content_type
    group_by_object = False

    QUANTITY = 'quantity'
    CONTENT_TYPE = 'content_type'
    OBJECT_ID = 'object_id'

    @action(detail=False, permission_classes=[IsAdminUser])
    def chartjs(self, request: HttpRequest):

        queryset: QuerySet = self.get_queryset()

        interval_param = request.GET.get(self.INTERVAL)
        aggregate_param = request.GET.get(self.AGGREGATE)
        end_param = request.GET.get(self.END)
        start_param = request.GET.get(self.START)
        self.group_by_object = request.GET.get(self.GROUP_BY_OBJECT)

        if end_param:
            queryset = queryset. \
                filter(**{self.date_field + '__lte': end_param})

        if start_param:
            queryset = queryset. \
                filter(**{self.date_field + '__gte': start_param})

        queryset_agregate = queryset \
            .annotate(interval=self.get_interval(interval_param))

        if self.group_by_object:
            queryset_agregate = queryset_agregate \
                .values(self.INTERVAL,
                        self.CONTENT_TYPE,
                        self.OBJECT_ID)
        else:
            queryset_agregate = queryset_agregate \
                .values(self.INTERVAL,
                        self.CONTENT_TYPE)

        queryset_agregate = queryset_agregate \
            .order_by(self.INTERVAL) \
            .annotate(quantity=self.get_aggregate(aggregate_param))

        if self.group_by_object:
            queryset_agregate = queryset_agregate \
                .values(self.INTERVAL,
                        self.CONTENT_TYPE,
                        self.OBJECT_ID,
                        self.QUANTITY)
        else:
            queryset_agregate = queryset_agregate \
                .values(self.INTERVAL,
                        self.CONTENT_TYPE,
                        self.QUANTITY)

        intervals = self.get_intervals(queryset_agregate)

        data_sets = self.get_datasets(queryset_agregate)

        response_data = {
            'labels': intervals,
            'datasets':
                data_sets
        }

        return Response(
            status=status.HTTP_200_OK,
            data=response_data
        )

    def get_intervals(self, queryset):
        labels = set([data.get(self.INTERVAL) for data in queryset])
        labels = list(labels)
        labels.sort()

        return labels

    def get_datasets(self, queryset_agregate):

        data_set_types = self.get_data_set_types(queryset_agregate)

        data_sets = []
        for data_set_type in data_set_types:
            data_set = {
                'label': self.get_label(data_set_type),
                'data': self.get_data(
                    queryset_agregate, data_set_type)
            }
            data_sets.append(data_set)

        return data_sets

    def get_data_set_types(self, queryset_agregate):

        if self.group_by_object:

            data_set_types = set([
                (data.get(self.CONTENT_TYPE), data.get(self.OBJECT_ID))
                for data in queryset_agregate
            ])
        else:
            data_set_types = set([
                data.get(self.CONTENT_TYPE)
                for data in queryset_agregate
            ])

        return data_set_types

    def get_label(self, data_set_type):
        if self.group_by_object:
            content_type, object_id = data_set_type
            try:
                object_data = ContentType.objects \
                    .get(id=content_type) \
                    .get_object_for_this_type(id=object_id)

                return str(object_data)
            except ObjectDoesNotExist:
                content_type_name = ContentType.objects. \
                    get(id=content_type).name
                return f'{content_type_name} - {object_id}'

        else:
            return ContentType.objects.get(id=data_set_type).name

    def get_data(self, queryset_agregate, data_set_type):

        if self.group_by_object:
            content_type, object_id = data_set_type
            queryset_filtered = queryset_agregate.filter(
                **{
                    self.CONTENT_TYPE: content_type,
                    self.OBJECT_ID: object_id
                }
            )

        else:
            queryset_filtered = queryset_agregate.filter(
                **{
                    self.CONTENT_TYPE: data_set_type,
                }
            )

        return [dict(
            {'x': data.get(self.INTERVAL),
             'y': data.get(self.QUANTITY)
             })
            for data in queryset_filtered]

    def get_interval(self, interval_param):

        trunc_function = TruncMonth

        if interval_param == 'day':
            trunc_function = TruncDay

        if interval_param == 'week':
            trunc_function = TruncWeek

        if interval_param == 'month':
            trunc_function = TruncMonth

        if interval_param == 'year':
            trunc_function = TruncYear

        return trunc_function(self.date_field)

    def get_aggregate(self, aggregate_param):

        aggregate_function = Sum

        if aggregate_param == 'sum':
            aggregate_function = Sum

        if aggregate_param == 'count':
            aggregate_function = Count

        return aggregate_function(self.quantity_field)
