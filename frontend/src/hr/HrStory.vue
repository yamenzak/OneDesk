<template>
  <div ref="root" class="pb-12">
    <div v-if="needs.length" class="mt-5 flex flex-wrap gap-2">
      <Button v-for="one in needs" :key="one.key" variant="outline" :label="one.label" @click="$emit('today')">
        <template #prefix><span :class="[one.icon, TONE[one.tone]]" class="size-4" aria-hidden="true" /></template>
      </Button>
    </div>

    <Section v-if="story.people" :title="__('Employee')" icon="lucide-users" data-cards>
      <div class="grid gap-3 lg:grid-cols-2">
        <ChartCard v-if="departments.length" class="h-96">
          <BarChart :title="__('Headcount by Department')" :data="departments" x="label" y="count" horizontal :x-axis="wrapped" :y-axis="{ format: count }" :series-config="{ count: { label: __('Employee'), color: hue(0) } }" @select="(one) => go(`/desk/employee?status=Active&department=${encodeURIComponent(one.row.department || '')}`)" />
        </ChartCard>
        <ChartCard class="h-96">
          <BarChart :title="__('Joined and Left')" :data="story.people.moves" x="month" :y="['joined', 'left']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="whole" :series-config="moveSeries" @select="go('/desk/query-report/Employee Exits')" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="story.time" :title="__('Time')" icon="lucide-clock" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard class="h-96 lg:col-span-2">
          <BarChart :title="__('Attendance')" :subtitle="__('The last 30 days')" :data="story.time.attendance" x="day" :y="STATUSES" stacked :x-axis="{ timeGrain: 'day', format: dayName }" :y-axis="whole" :series-config="statusSeries" @select="go('/desk/query-report/Monthly Attendance Sheet')" />
        </ChartCard>
        <ChartCard v-if="leave.length" class="h-96">
          <DonutChart :title="__('Leave Taken This Year')" :data="leave" category="label" value="days" :format="days" :center-label="__('Taken')" :palette="ramp(1)" @select="go('/desk/query-report/Employee Leave Balance Summary')" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="story.pay" :title="__('Pay')" icon="lucide-banknote" data-cards>
      <div class="grid gap-3 lg:grid-cols-3">
        <ChartCard class="h-96 lg:col-span-2">
          <BarChart :title="__('Payroll')" :data="story.pay.payroll" x="month" :y="['gross', 'net']" :x-axis="{ timeGrain: 'month', format: monthName }" :y-axis="{ format: cash }" :series-config="paySeries" @select="go('/desk/query-report/Salary Register')" />
        </ChartCard>
        <ChartCard v-if="expenses.length" class="h-96">
          <DonutChart :title="__('Expense Claims This Year')" :data="expenses" category="label" value="amount" :format="cash" :center-label="__('Claimed')" :palette="ramp(4)" @select="go('/desk/expense-claim')" />
        </ChartCard>
      </div>
    </Section>

    <Section v-if="funnel.length" :title="__('Hiring')" icon="lucide-user-plus" data-cards>
      <ChartCard class="h-72">
        <FunnelChart :title="__('Hiring Funnel')" :subtitle="__('Applicants of the last 12 months')" :data="funnel" category="label" value="count" :format="count" @select="(one) => go(FUNNEL[one.row.step])" />
      </ChartCard>
    </Section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { BarChart, ChartCard, DonutChart, FunnelChart, useChartTokens } from "frappe-ui/charts";

import { __, count, date, go, money, Section, shortMonth, wrapped } from "../kit";

const TONE = { late: "text-ink-red-5", soon: "text-ink-amber-6", left: "text-ink-gray-5" };
const STATUSES = ["Present", "Work From Home", "Half Day", "On Leave", "Absent"];

const props = defineProps({ story: { type: Object, required: true }, needs: { type: Array, default: () => [] } });
defineEmits(["today"]);

const root = ref();
const { tokens } = useChartTokens(root);
const hue = (i) => tokens.value.categorical[i % tokens.value.categorical.length];
const ramp = (from) => {
  const all = tokens.value.categorical;
  return [...all.slice(from), ...all.slice(0, from)];
};

const cash = (value) => money(value, props.story.currency, 0);
const days = (value) => __("{0} days", [value]);
const monthName = (value) => shortMonth(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));
const dayName = (value) => date(typeof value === "string" ? value : new Date(value).toISOString().slice(0, 10));
const whole = { format: count, echartOptions: { minInterval: 1 } };

const departments = computed(() => (props.story.people?.departments || []).map((one) => ({ ...one, label: one.label || __("Not Recorded") })));
const leave = computed(() => (props.story.time?.leave || []).map((one) => ({ ...one, label: __(one.leave_type) })));
const expenses = computed(() => (props.story.pay?.expenses || []).map((one) => ({ ...one, label: __(one.expense_type) })));
const funnel = computed(() => (props.story.hiring?.funnel || []).map((one) => ({ ...one, label: __(one.step) })));

const moveSeries = computed(() => ({ joined: { label: __("Joined"), color: hue(2) }, left: { label: __("Left"), color: hue(6) } }));
const paySeries = computed(() => ({ gross: { label: __("Gross Pay"), color: hue(0) }, net: { label: __("Net Pay"), color: hue(2) } }));
const statusSeries = computed(() => ({
  Present: { label: __("Present"), color: hue(2) },
  "Work From Home": { label: __("Work From Home"), color: hue(0) },
  "Half Day": { label: __("Half Day"), color: hue(4) },
  "On Leave": { label: __("On Leave"), color: hue(5) },
  Absent: { label: __("Absent"), color: hue(6) },
}));

const FUNNEL = {
  "Job Applicant": "/desk/job-applicant",
  Interview: "/desk/interview",
  "Job Offer": "/desk/job-offer",
  Accepted: "/desk/job-offer?status=Accepted",
  Joined: '/desk/employee?job_applicant=["is","set"]',
};
</script>
