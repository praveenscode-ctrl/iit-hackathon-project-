class UserModel {
  final String id;
  final String fullName;
  final String email;
  final String role;
  final String? classId;
  final String? className;
  final String? registrationId;
  final String status;

  UserModel({
    required this.id,
    required this.fullName,
    required this.email,
    required this.role,
    this.classId,
    this.className,
    this.registrationId,
    required this.status,
  });

  factory UserModel.fromJson(Map<String, dynamic> j) => UserModel(
        id: j['id'] as String,
        fullName: (j['full_name'] ?? '') as String,
        email: (j['email'] ?? '') as String,
        role: (j['role'] ?? '') as String,
        classId: j['class_id'] as String?,
        className: j['class_name'] as String?,
        registrationId: j['registration_id'] as String?,
        status: (j['status'] ?? 'ACTIVE') as String,
      );
}
