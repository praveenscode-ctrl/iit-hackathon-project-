import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/class_service.dart';
import '../../core/exceptions.dart';

class CreateClassScreen extends StatefulWidget {
  const CreateClassScreen({super.key});

  @override
  State<CreateClassScreen> createState() => _CreateClassScreenState();
}

class _CreateClassScreenState extends State<CreateClassScreen> {
  final _nameCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _yearCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  final _svc = ClassService();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _descCtrl.dispose();
    _yearCtrl.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) {
      setState(() => _error = 'Class name is required');
      return;
    }

    setState(() { _loading = true; _error = null; });

    try {
      await _svc.createClass(
        className: name,
        description: _descCtrl.text.trim().isEmpty ? null : _descCtrl.text.trim(),
        academicYear: _yearCtrl.text.trim().isEmpty ? null : _yearCtrl.text.trim(),
      );
      if (!mounted) return;
      context.pop();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Failed to create class');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Class')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _nameCtrl,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Class Name *', prefixIcon: Icon(Icons.school_outlined)),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _descCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Description',
                alignLabelWithHint: true,
                prefixIcon: Icon(Icons.notes_outlined),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _yearCtrl,
              decoration: const InputDecoration(
                labelText: 'Academic Year',
                hintText: 'e.g. 2024-25',
                prefixIcon: Icon(Icons.calendar_today_outlined),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(_error!, style: TextStyle(fontSize: 13, color: Colors.red.shade700)),
              ),
            ],
            const SizedBox(height: 28),
            ElevatedButton(
              onPressed: _loading ? null : _create,
              child: _loading
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Create Class', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }
}
