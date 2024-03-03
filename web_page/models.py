from django.db import models
from django.utils import timezone


class Course(models.Model):
    name = models.CharField(max_length=255)


class Task(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=2048)
    created_at = models.DateTimeField(default=timezone.now)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)


class File(models.Model):
    path = models.CharField(max_length=255)
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE)


class Formula(models.Model):
    expression = models.CharField(max_length=100)
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE)


class Variable(models.Model):
    name = models.CharField(max_length=10)
    formula_id = models.ForeignKey(Formula, on_delete=models.CASCADE)


class Mapping(models.Model):
    key = models.CharField(max_length=100)
    value = models.FloatField(max_length=10)
    variable_id = models.ForeignKey(Variable, on_delete=models.CASCADE)
