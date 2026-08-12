"""Serialiseurs des referentiels."""
from rest_framework import serializers

from .models import Currency, Donor, ExchangeRate, Organization, Sector, Zone


class ZoneSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    full_path = serializers.CharField(read_only=True)
    nb_enfants = serializers.IntegerField(source="children.count", read_only=True)

    class Meta:
        model = Zone
        fields = ["id", "code", "name", "level", "level_label", "parent", "parent_name",
                  "full_path", "latitude", "longitude", "nb_enfants"]


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "code", "label", "parent", "is_active"]


class DonorSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Donor
        fields = ["id", "name", "acronym", "type", "type_label", "country",
                  "contact_email", "logo", "is_active"]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "symbol", "is_base"]


class ExchangeRateSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency.code", read_only=True)
    base_code = serializers.CharField(source="base_currency.code", read_only=True)

    class Meta:
        model = ExchangeRate
        fields = ["id", "currency", "currency_code", "base_currency", "base_code",
                  "rate", "effective_date"]


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "acronym", "address", "phone", "email", "logo", "legal_notice"]