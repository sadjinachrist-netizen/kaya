"""Serialiseurs des financements et du budget."""
from rest_framework import serializers

from .models import (
    BudgetLine,
    Expense,
    Grant,
    GrantProject,
    Installment,
    ReportDeadline,
)


class GrantProjectSerializer(serializers.ModelSerializer):
    project_code = serializers.CharField(source="project.code", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta:
        model = GrantProject
        fields = ["id", "grant", "project", "project_code", "project_title", "share_percent"]

    def validate(self, attrs):
        instance = GrantProject(**{**attrs, "pk": getattr(self.instance, "pk", None)})
        if self.instance:
            instance.pk = self.instance.pk
        try:
            instance.clean()
        except Exception as erreur:
            raise serializers.ValidationError(getattr(erreur, "message_dict", str(erreur)))
        return attrs


class BudgetLineSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    montant_depense = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    montant_disponible = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    taux_consommation = serializers.FloatField(read_only=True)
    est_depassee = serializers.BooleanField(read_only=True)
    nb_enfants = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = BudgetLine
        fields = ["id", "grant", "code", "label", "category", "category_label",
                  "budgeted_amount", "parent", "nb_enfants",
                  "montant_depense", "montant_disponible", "taux_consommation",
                  "est_depassee"]


class ReportDeadlineSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    jours_restants = serializers.IntegerField(read_only=True)
    alerte = serializers.CharField(read_only=True)

    class Meta:
        model = ReportDeadline
        fields = ["id", "grant", "type", "type_label", "due_date", "status",
                  "status_label", "submitted_at", "document",
                  "jours_restants", "alerte"]


class InstallmentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Installment
        fields = ["id", "grant", "amount", "expected_date", "received_date",
                  "status", "status_label"]


class ExpenseSerializer(serializers.ModelSerializer):
    budget_line_code = serializers.CharField(source="budget_line.code", read_only=True)
    project_code = serializers.CharField(source="project.code", read_only=True)
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    entered_by_name = serializers.CharField(source="entered_by.full_name", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "budget_line", "budget_line_code", "project", "project_code",
                  "label", "amount", "currency", "currency_code", "expense_date",
                  "receipt", "status", "status_label",
                  "entered_by", "entered_by_name", "validated_by", "created_at"]
        read_only_fields = ["status", "entered_by", "validated_by", "created_at"]

    def validate(self, attrs):
        """Controle la periode d'eligibilite avant enregistrement."""
        ligne = attrs.get("budget_line") or getattr(self.instance, "budget_line", None)
        date_depense = attrs.get("expense_date") or getattr(self.instance, "expense_date", None)
        if ligne and date_depense:
            financement = ligne.grant
            if not (financement.eligibility_start <= date_depense <= financement.eligibility_end):
                raise serializers.ValidationError({"expense_date": (
                    f"Depense hors periode d'eligibilite "
                    f"({financement.eligibility_start} au {financement.eligibility_end})."
                )})
        return attrs


class GrantListSerializer(serializers.ModelSerializer):
    donor_name = serializers.CharField(source="donor.acronym", read_only=True)
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    taux_consommation = serializers.FloatField(read_only=True)
    taux_temps_ecoule = serializers.FloatField(read_only=True)
    ecart_rythme = serializers.FloatField(read_only=True)
    alerte_rythme = serializers.CharField(read_only=True)

    class Meta:
        model = Grant
        fields = ["id", "contract_number", "title", "donor", "donor_name",
                  "amount", "currency", "currency_code", "status", "status_label",
                  "eligibility_start", "eligibility_end",
                  "taux_consommation", "taux_temps_ecoule", "ecart_rythme", "alerte_rythme"]


class GrantDetailSerializer(GrantListSerializer):
    project_links = GrantProjectSerializer(many=True, read_only=True)
    budget_lines = serializers.SerializerMethodField()
    deadlines = ReportDeadlineSerializer(many=True, read_only=True)
    installments = InstallmentSerializer(many=True, read_only=True)
    quote_part_totale = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    budget_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    montant_depense = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    montant_disponible = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta(GrantListSerializer.Meta):
        fields = GrantListSerializer.Meta.fields + [
            "signature_date", "document", "created_at",
            "quote_part_totale", "budget_total", "montant_depense", "montant_disponible",
            "project_links", "budget_lines", "deadlines", "installments",
        ]

    def get_budget_lines(self, obj):
        """Seules les lignes de premier niveau ; les enfants suivront par requete."""
        racines = obj.budget_lines.filter(parent__isnull=True)
        return BudgetLineSerializer(racines, many=True).data