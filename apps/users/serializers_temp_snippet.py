
class StaffCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating staff members.
    Handles password hashing and default role assignment.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "username", "password"]
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        # Ensure username is set (frontend sends email as username, but just in case)
        if 'username' not in validated_data:
             validated_data['username'] = validated_data.get('email')
             
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
