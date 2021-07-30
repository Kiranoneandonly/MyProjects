# -*- coding: utf-8 -*-
"""A comprehensive view of a project's prices and costs."""

# This is perhaps the third generation of such a view, previous iterations being the
# viewmodels.ProjectTargetSetViewModel hierarchy and price_viewmodels.
import decimal
from collections import defaultdict, OrderedDict

from copy import copy
from decimal import Decimal, localcontext, ExtendedContext

from django.conf import settings
import math
from django.utils.encoding import force_str
from django.utils.timezone import now
from prices.constants import MINIMUM_JOB_SURCHARGE
from projects.duedates import get_job_express_duration, get_job_standard_duration
from shared.utils import calculate_gross_margin

LEVEL_ASSET = 'asset'
LEVEL_TASK = 'task'
LEVEL_LANGUAGE = 'language'
LEVEL_PROJECT = 'project'

LEVELS = [
    LEVEL_ASSET,
    LEVEL_TASK,
    LEVEL_LANGUAGE,
    LEVEL_PROJECT
]

FOUR_PLACES = Decimal('1.0000')
zero = Decimal(0)


class ProjectQuote(object):
    """
    :ivar dict[Locale, QuoteItem] targets: quote for each target locale
    :ivar dict[Locale, list[QuoteItem]] target_details: a target's list of task-quotes
    :ivar dict[Task, QuoteItem] tasks: quote for each task
    :ivar dict[Task, list[QuoteItem]] task_details: a task's list of asset-quotes
    :ivar QuoteItem total: sum total for this project
    :ivar dict[Task, dict[FileAsset, QuoteItem]] assets: look up quote by task and asset
    """

    def __init__(self, project, speed=None, include_price=True, include_costs=True, quote_summary=False, task=None, recalculate_flag=False, tat_custom=False, sub_tasks=False):
        """
        :type project: projects.models.Project
        """
        from tasks.models import TaskQuote, TaskAssetQuote
        from projects.models import PriceQuote, PriceQuoteDetails

        if speed is None:
            speed = project.project_speed
        self.project = project
        self.speed = speed
        self.include_price = include_price
        self.include_costs = include_costs
        self.created_at = now()

        if quote_summary or not project.has_price():

            tasks_for_pricing = []

            if task:
                recalculate_flag = True
                self.tasks, self.task_details, self.express_tasks, self.express_task_details = self._load_tasks(task=task, recalculate_flag=recalculate_flag, tat_custom=tat_custom)
                tasks_for_pricing.append(task)
            elif sub_tasks:
                self.tasks, self.task_details = self._load_tasks(sub_tasks=sub_tasks)
            else:
                self.tasks, self.task_details, self.express_tasks, self.express_task_details = self._load_tasks(recalculate_flag=recalculate_flag, tat_custom=tat_custom)
                tasks_for_pricing = project.task_set.select_for_pricing()

            self.targets, self.target_details = self._summarize_targets(self.tasks.values())
            self.express_targets, self.express_target_details = self._summarize_targets(self.express_tasks.values())

            if not include_costs:
                return

            if task is None:
                if self.tasks:
                    self.total = self._summarize_project(self.targets.values())
                if self.express_tasks:
                    self.express_total = self._summarize_project(self.express_targets.values())
                else:
                    self.total = QuoteItem()
                    self.express_total = QuoteItem()
                    self.total.level = LEVEL_PROJECT

            #: :type: dict[Task, dict[FileAsset, QuoteItem]]
            self.assets = {}
            for task, asset_quotes in self.task_details.items():
                self.assets[task] = {aq.asset: aq for aq in asset_quotes}

            self.express_assets = {}
            for task, asset_quotes in self.express_task_details.items():
                self.express_assets[task] = {aq.asset: aq for aq in asset_quotes}

            total_wordcount = asset_wordcount = 0
            for task in tasks_for_pricing:
                task_quote = self.tasks[task]
                express_task_quote = self.express_tasks[task]

                task_quote.cost = task_quote.cost if task_quote.cost else zero
                task_quote.raw_price = task_quote.raw_price if task_quote.raw_price else zero
                task_quote.price = task_quote.price if task_quote.price else zero

                if task_quote.analysis not in (None, MINIMUM_JOB_SURCHARGE):
                    total_wordcount = task_quote.analysis.total_wordcount() if task_quote.analysis is not None else 0

                express_task_quote.cost = express_task_quote.cost if express_task_quote.cost else zero
                express_task_quote.raw_price = express_task_quote.raw_price if express_task_quote.raw_price else zero
                express_task_quote.price = express_task_quote.price if express_task_quote.price else zero

                for asset_quote in self.task_details[task]:
                    item_asset = None
                    if asset_quote.analysis not in (None, MINIMUM_JOB_SURCHARGE):
                        item_asset = asset_quote.analysis.asset
                        asset_wordcount = asset_quote.analysis.total_wordcount()

                    asset_quote_object, created = TaskAssetQuote.objects.get_or_create(task=task, asset=item_asset, target=task.service.target)

                    if asset_quote_object:
                        asset_quote_object.asset_total_cost = asset_quote.cost
                        asset_quote_object.asset_raw_price = asset_quote.raw_price
                        asset_quote_object.asset_mbd = asset_quote.memory_bank_discount
                        asset_quote_object.asset_net_price = asset_quote.price
                        asset_quote_object.asset_gm = asset_quote.gross_margin
                        asset_quote_object.asset_is_minimum_price = asset_quote.is_minimum_price
                        asset_quote_object.asset_wordcount = asset_wordcount
                        asset_quote_object.save()

                for asset_quote in self.express_task_details[task]:
                    item_asset = None
                    if asset_quote.analysis not in (None, MINIMUM_JOB_SURCHARGE):
                        item_asset = asset_quote.analysis.asset

                    asset_quote_object, created = TaskAssetQuote.objects.get_or_create(task=task, asset=item_asset, target=task.service.target)

                    if asset_quote_object:
                        asset_quote_object.asset_total_express_cost = asset_quote.cost
                        asset_quote_object.asset_express_raw_price = asset_quote.raw_price
                        asset_quote_object.asset_express_mbd = asset_quote.memory_bank_discount
                        asset_quote_object.asset_express_net_price = asset_quote.price
                        asset_quote_object.asset_express_gm = asset_quote.gross_margin
                        asset_quote_object.save()

                if task.is_translation():
                    for asset_quote in self.task_details[task]:
                        item_asset = None
                        if asset_quote.analysis not in (None, MINIMUM_JOB_SURCHARGE):
                            item_asset = asset_quote.analysis.asset
                            wordcount = asset_quote.analysis.total_wordcount()

                        asset_quote_object, created = TaskAssetQuote.objects.get_or_create(task=task, asset=item_asset, target=task.service.target)

                        if asset_quote_object:
                            asset_quote_object.asset_total_cost = asset_quote.cost
                            asset_quote_object.asset_raw_price = asset_quote.raw_price
                            asset_quote_object.asset_mbd = asset_quote.memory_bank_discount
                            asset_quote_object.asset_net_price = asset_quote.price
                            asset_quote_object.asset_gm = asset_quote.gross_margin
                            asset_quote_object.asset_is_minimum_price = asset_quote.is_minimum_price
                            asset_quote_object.asset_wordcount = wordcount
                            asset_quote_object.save()

                    for asset_quote in self.express_task_details[task]:
                        item_asset = None
                        if asset_quote.analysis not in (None, MINIMUM_JOB_SURCHARGE):
                            item_asset = asset_quote.analysis.asset

                        asset_quote_object, created = TaskAssetQuote.objects.get_or_create(task=task, asset=item_asset)

                        if asset_quote_object:
                            asset_quote_object.asset_total_express_cost = asset_quote.cost
                            asset_quote_object.asset_express_raw_price = asset_quote.raw_price
                            asset_quote_object.asset_express_mbd = asset_quote.memory_bank_discount
                            asset_quote_object.asset_express_net_price = asset_quote.price
                            asset_quote_object.asset_express_gm = asset_quote.gross_margin
                            asset_quote_object.save()

                quote_object, created = TaskQuote.objects.get_or_create(task=task, project=project)
                if quote_object:
                    quote_object.total_cost = task_quote.cost
                    quote_object.raw_price = task_quote.raw_price
                    quote_object.mbd = task_quote.memory_bank_discount
                    quote_object.net_price = task_quote.price
                    quote_object.gm = task_quote.gross_margin
                    quote_object.wordcount = total_wordcount

                    quote_object.total_express_cost = express_task_quote.cost
                    quote_object.express_raw_price = express_task_quote.raw_price
                    quote_object.express_mbd = express_task_quote.memory_bank_discount
                    quote_object.express_net_price = express_task_quote.price
                    quote_object.express_gm = express_task_quote.gross_margin

                    quote_object.standard_tat = task.standard_days
                    quote_object.express_tat = task.express_days

                    quote_object.save()

            price_quote, created = PriceQuote.objects.get_or_create(project=project)

            for target, target_quote in self.targets.items():

                price_quote_details, created = PriceQuoteDetails.objects.get_or_create(pricequote=price_quote, target=target)

                if recalculate_flag:

                    pqd_summary = price_quote_details.sum_details_taskquote()
                    if pqd_summary:
                        price_quote_details.target_price = pqd_summary['net_price__sum'] if pqd_summary['net_price__sum'] else 0
                        price_quote_details.target_cost = pqd_summary['total_cost__sum'] if pqd_summary['total_cost__sum'] else 0
                        price_quote_details.target_gross_margin = calculate_gross_margin(price_quote_details.target_price, price_quote_details.target_cost)
                        price_quote_details.target_standard_tat = pqd_summary['standard_tat__sum'] if pqd_summary['standard_tat__sum'] else 0

                else:
                    price_quote_details.target_price = target_quote.price
                    price_quote_details.target_cost = target_quote.cost
                    price_quote_details.target_gross_margin = target_quote.gross_margin
                    price_quote_details.target_standard_tat = self.targets[target].turn_around_time

                price_quote_details.save()

            for target, target_quote in self.express_targets.items():

                price_quote_details, created = PriceQuoteDetails.objects.get_or_create(pricequote=price_quote, target=target)

                if recalculate_flag:

                    pqd_express_summary = price_quote_details.sum_details_taskquote()

                    if pqd_express_summary:
                        price_quote_details.target_express_price = pqd_express_summary['express_net_price__sum'] if pqd_express_summary['express_net_price__sum'] else 0
                        price_quote_details.target_express_cost =  pqd_express_summary['total_express_cost__sum'] if pqd_express_summary['total_express_cost__sum'] else 0
                        price_quote_details.target_express_gross_margin = calculate_gross_margin(price_quote_details.target_express_price, price_quote_details.target_express_cost)
                        price_quote_details.target_express_tat =  pqd_express_summary['express_tat__sum'] if pqd_express_summary['express_tat__sum'] else 0
                else:
                    price_quote_details.target_express_price = target_quote.price
                    price_quote_details.target_express_cost = target_quote.cost
                    price_quote_details.target_express_gross_margin = target_quote.gross_margin
                    price_quote_details.target_express_tat = self.express_targets[target].turn_around_time

                price_quote_details.save()

            if price_quote:
                if recalculate_flag:

                    pq_summary = price_quote.sum_details()

                    if pq_summary:
                        price_quote.price = pq_summary['target_price__sum'] if pq_summary['target_price__sum'] else 0
                        price_quote.cost = pq_summary['target_cost__sum'] if pq_summary['target_cost__sum'] else 0
                        price_quote.gm = calculate_gross_margin(price_quote.price, price_quote.cost)

                        price_quote.express_price = pq_summary['target_express_price__sum'] if pq_summary['target_express_price__sum'] else 0
                        price_quote.express_cost = pq_summary['target_express_cost__sum'] if pq_summary['target_express_cost__sum'] else 0
                        price_quote.express_gm = calculate_gross_margin(Decimal(price_quote.express_price), Decimal(price_quote.express_cost))

                    price_quote.standard_tat, price_quote.express_tat = project.calc_project_tat(price_quote)

                else:
                    price_quote.price = self.total.price
                    price_quote.cost = self.total.cost
                    price_quote.gm = self.total.gross_margin
                    price_quote.express_price = self.express_total.price
                    price_quote.express_cost = self.express_total.cost
                    price_quote.express_gm = self.express_total.gross_margin
                    price_quote.standard_tat = self.total.turn_around_time
                    price_quote.express_tat = self.express_total.turn_around_time
                    price_quote.wordcount = total_wordcount

                # todo generate next version # of PriceQuote automatically
                price_quote.version = None
                price_quote.active = True
                price_quote.save()

        else:
            self.tasks, self.task_details, self.express_tasks, self.express_task_details = self._load_tasks(sub_tasks=sub_tasks)
            self.targets, self.target_details = self._summarize_targets(self.tasks.values())

            if self.tasks:
                self.total = self._summarize_project(self.targets.values())
            else:
                self.total = QuoteItem()
                self.total.level = LEVEL_PROJECT

            #: :type: dict[Task, dict[FileAsset, QuoteItem]]
            self.assets = {}
            for task, asset_quotes in self.task_details.items():
                self.assets[task] = {aq.asset: aq for aq in asset_quotes}

    def _load_tasks(self, task=None, recalculate_flag=False, tat_custom=False, sub_tasks=False):
        """
        :rtype: dict[Task, QuoteItem], dict[Task, list[QuoteItem]]
        """
        from projects.models import EXPRESS_SPEED, STANDARD_SPEED
        tasks = []
        if task:
            tasks.append(task)
            self.include_price = True
            self.include_costs = True
        elif sub_tasks:
            tasks = self.project.task_set.select_for_pricing()
        else:
            tasks = self.project.task_set.filter(parent_id=None).select_for_pricing()

        summaries = {}
        base_items = []
        percentage_tasks_non_client_discount = []
        percentage_tasks_client_discount = []
        task_details = {}
        express_summaries = {}
        express_base_items = []
        express_task_details = {}

        for task in tasks:
            if recalculate_flag and not tat_custom:
                if task.is_translation():
                    from shared.viewmodels import TargetAnalysisSetViewModel
                    target_analysis = TargetAnalysisSetViewModel(task.service.target, task.project, include_placeholder=False)
                    mbd = target_analysis.total_memory_bank_discount / 100
                    wc = target_analysis.total_words
                    if wc:
                        standard_days = get_job_standard_duration(wordcount=wc, mbd=float(mbd))
                        express_days = get_job_express_duration(wordcount=wc, mbd=float(mbd))
                        if standard_days <= express_days:
                            standard_days = express_days + 1

                        from tasks.models import TranslationTask
                        tt = TranslationTask.objects.get(pk=task.id)
                        tt.standard_days = standard_days
                        tt.express_days = express_days
                        tt.save()

            if task.percentage_based():
                if task.is_client_discount():
                    percentage_tasks_client_discount.append(task)
                    continue
                else:
                    percentage_tasks_non_client_discount.append(task)
                    continue

            task_summary, task_items = QuoteItem.create_from_task(
                task, STANDARD_SPEED, self.include_price, self.include_costs)

            task_express_summary, task_express_items = QuoteItem.create_from_task(
                task, EXPRESS_SPEED, self.include_price, self.include_costs)

            summaries[task] = task_summary
            base_items.extend(task_items)
            task_details[task] = task_items

            express_summaries[task] = task_express_summary
            express_base_items.extend(task_express_items)
            express_task_details[task] = task_express_items

        for task in percentage_tasks_non_client_discount:
            task_summary, task_items = QuoteItem.create_from_percentage_task(
                task, base_items, STANDARD_SPEED, self.include_costs)

            task_express_summary, task_express_items = QuoteItem.create_from_percentage_task(
                task, express_base_items, EXPRESS_SPEED, self.include_costs)

            summaries[task] = task_summary
            base_items.extend(task_items)
            task_details[task] = task_items

            express_summaries[task] = task_express_summary
            express_base_items.extend(task_express_items)
            express_task_details[task] = task_express_items

        for task in percentage_tasks_client_discount:
            task_summary, task_items = QuoteItem.create_from_percentage_task(
                task, base_items, STANDARD_SPEED, self.include_costs)

            task_express_summary, task_express_items = QuoteItem.create_from_percentage_task(
                task, express_base_items, EXPRESS_SPEED, self.include_costs)

            summaries[task] = task_summary
            task_details[task] = task_items

            express_summaries[task] = task_express_summary
            express_task_details[task] = task_express_items

        return summaries, task_details, express_summaries, express_task_details

    def _summarize_targets(self, quote_items):
        """
        :rtype: dict[Locale, QuoteItem], dict[Locale, list[QuoteItem]]
        """
        items_by_target = defaultdict(list)
        target_summaries = []

        for item in quote_items:
            items_by_target[item.target].append(item)

        for target, target_items in items_by_target.iteritems():
            summary = QuoteItem.summarize(target_items)
            target_items.sort(key=self._task_sort_key)
            target_summaries.append((target, summary))

        target_summaries.sort(key=lambda pair: pair[0].description)
        return OrderedDict(target_summaries), items_by_target

    def _summarize_project(self, quote_items):
        return QuoteItem.summarize(quote_items)

    def itemized_flat(self, billable_only=True):
        for target in self.targets:
            target_items = self.target_details[target]
            for task_item in target_items:
                task = task_item.task
                if billable_only and not task.billable:
                    continue
                for item in self.task_details[task]:
                    yield item

    @staticmethod
    def _task_sort_key(quote_item):
        task = quote_item.task
        non_workflow = 1 if (not task.service.service_type.workflow) else 0
        is_percentage = 1 if task.percentage_based() else 0
        # Sorting by predecessor_id will put root tasks first and then put
        # things with earlier-created predecessors before later-created ones.
        # If you manually reordered tasks, this would give some other order,
        # but it should work fine for most cases and the order isn't
        # absolutely critical to the view.
        return non_workflow, is_percentage, task.predecessor_id


class QuoteItem(object):
    level = None
    speed = None
    target = None
    task = None
    asset = None
    analysis = None
    raw_price = None
    price = None
    raw_price_calc_mbd = None
    price_calc_mbd = None
    memory_bank_discount = None
    raw_cost = None
    cost = None
    cost_memory_bank_discount = None
    gross_margin = None
    turn_around_time = None
    is_minimum_price = False
    express_price = None

    def __init__(self):
        pass

    def __getitem__(self, key):
        return self.data[key]

    @classmethod
    def create_from_task(cls, task, speed, include_price=True, include_cost=True):
        from projects.models import EXPRESS_SPEED

        items = []

        items_by_analysis = {}

        item_template = cls()
        item_template.level = LEVEL_ASSET
        item_template.speed = speed
        item_template.target = task.service.target
        item_template.task = task

        if include_price:
            price_details = task.itemized_price_details(speed)
            for item_price in price_details:
                item = copy(item_template)
                item.analysis = item_price.analysis
                if item.analysis == MINIMUM_JOB_SURCHARGE:
                    item.is_minimum_price = True
                if item.analysis in (None, MINIMUM_JOB_SURCHARGE):
                    item.asset = item.analysis
                else:
                    item.asset = item.analysis.asset
                item.price = item_price.net
                item.raw_price = item_price.raw
                item.memory_bank_discount = item_price.mbd if not math.isnan(item_price.mbd) else zero
                items.append(item)
                items_by_analysis[item.analysis] = item

        if include_cost:
            cost_details = task.itemized_cost_details()

            for item_cost in cost_details:
                if item_cost.analysis in items_by_analysis:
                    item = items_by_analysis[item_cost.analysis]
                else:
                    item = copy(item_template)
                    item.analysis = item_cost.analysis
                    if item.analysis in (None, MINIMUM_JOB_SURCHARGE):
                        item.asset = item.analysis
                    else:
                        item.asset = item.analysis.asset
                    items.append(item)

                item.cost = Decimal(item_cost.net) if (item_cost.net is not None) else None
                item.raw_cost = Decimal(item_cost.raw) if (item_cost.raw is not None) else None
                item.cost_memory_bank_discount = item_cost.mbd if not math.isnan(item_cost.mbd) else zero

        if items:
            summary = cls.summarize(items)
        else:
            # no-price and no-cost summaries end up here.
            summary = copy(item_template)
            summary.level = LEVEL_TASK
            # analysis?

        summary.turn_around_time = task.express_days if (speed == EXPRESS_SPEED) else task.standard_days

        return summary, items

    @classmethod
    def create_from_percentage_task(cls, task, quote_items, speed, include_cost=True):
        from projects.models import EXPRESS_SPEED

        summary = task.quote_percentage_of(quote_items, speed)

        if speed == EXPRESS_SPEED:
            multiplier = Decimal(task.project.express_factor)
        else:
            multiplier = 1
        price_details = task.nontranslationtask._itemized_price_details(task.project.kit, task.service.target, multiplier, summary.price)

        items = []
        item_template = cls()
        item_template.level = LEVEL_ASSET
        item_template.speed = speed
        item_template.target = task.service.target
        item_template.task = task

        for item_price in price_details:
            item = copy(item_template)
            item.analysis = item_price.analysis
            if item.analysis == MINIMUM_JOB_SURCHARGE:
                item.is_minimum_price = True
            if item.analysis in (None, MINIMUM_JOB_SURCHARGE):
                item.asset = item.analysis
            else:
                item.asset = item.analysis.asset
            item.price = item_price.net
            item.raw_price = item_price.raw
            item.memory_bank_discount = item_price.mbd if not math.isnan(item_price.mbd) else zero
            items.append(item)

        return summary, items

    @classmethod
    def summarize(cls, items):
        if not items:
            raise ValueError("Attempted to summarize zero items.")

        summary = cls()
        input_level_index = LEVELS.index(items[0].level)
        level_index = input_level_index + 1

        summary.level = LEVELS[level_index]

        # oh for a comparable enum type (use t.p.constants?)
        if level_index <= LEVELS.index(LEVEL_TASK):
            summary.task = items[0].task
            summary.analysis = sum((item.analysis for item in items[1:]
                                    if item.analysis not in (MINIMUM_JOB_SURCHARGE, None)),
                                   items[0].analysis)
        else:
            summary.analysis = items[0].analysis

        if level_index <= LEVELS.index(LEVEL_LANGUAGE):
            summary.target = items[0].target

        if summary.level == LEVEL_TASK:
            summary.turn_around_time = items[0].turn_around_time
            summary.is_minimum_price = any(i.is_minimum_price for i in items)
        elif summary.level == LEVEL_LANGUAGE:
            summary.turn_around_time = sum(
                (qi.turn_around_time for qi in items if qi.turn_around_time))
        elif summary.level == LEVEL_PROJECT:
            summary.turn_around_time = max(qi.turn_around_time for qi in items)

        summary.speed = items[0].speed

        summary.cost = sum_decimal_or_none(qi.cost for qi in items)
        summary.raw_cost = sum_decimal_or_none(qi.raw_cost for qi in items)
        summary.price = sum_decimal_or_none(qi.price for qi in items)
        summary.raw_price = sum_decimal_or_none(qi.raw_price for qi in items)

        # get mbd even if for minimum jobs to display in the UI
        summary.price_calc_mbd = sum_decimal_or_none(qi.price for qi in items if not qi.is_minimum_price)
        summary.raw_price_calc_mbd = sum_decimal_or_none(qi.raw_price for qi in items if not qi.is_minimum_price)

        with localcontext(ExtendedContext):
            if None not in [summary.price_calc_mbd, summary.raw_price_calc_mbd]:
                summary.memory_bank_discount = (summary.price_calc_mbd / summary.raw_price_calc_mbd) - 1
                summary.memory_bank_discount = summary.memory_bank_discount if not math.isnan(summary.memory_bank_discount) else zero

            if None not in [summary.cost, summary.raw_cost]:
                summary.cost_memory_bank_discount = (summary.cost / summary.raw_cost) - 1
                summary.cost_memory_bank_discount = summary.cost_memory_bank_discount if not math.isnan(summary.cost_memory_bank_discount) else zero

        return summary

    @property
    def gross_margin(self):
        if self.price is None:
            return None

        cost = self.cost if (self.cost is not None) else zero

        # Allow returning Infinity instead of raising an exception.
        with localcontext(ExtendedContext):
            gm = ((self.price - cost) / self.price).quantize(FOUR_PLACES)
            return gm if not math.isnan(gm) else zero

    def __repr__(self):
        class_name = self.__class__.__name__
        what = self.task or self.target or u"Project"
        s = ("<%(class_name)s %(speed)s %(what)s%(asset)s "
             "P:%(price)s C:%(cost)s> " % {
                 'class_name': class_name,
                 'speed': self.speed,
                 'what': what,
                 'asset': (' ' + self.asset.orig_name) if self.asset else '',
                 'price': self.price,
                 'cost': self.cost,
             })
        return force_str(s)


def sum_decimal_or_none(elements):
    return sum((i for i in elements if i is not None), zero)
