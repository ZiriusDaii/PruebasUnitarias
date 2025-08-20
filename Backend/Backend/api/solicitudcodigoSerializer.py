from rest_framework import serializers
from api.usuarios.models import Usuario

class SolicitudCodigoSerializer(serializers.Serializer):
    correo_electronico = serializers.EmailField()

    def validate_correo(self, value):
        if not Usuario.objects.filter(correo_electronico=value).exists():
            raise serializers.ValidationError("No existe un usuario con ese correo.")
        return value
