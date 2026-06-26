import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../providers/ai_provider.dart';
import '../../providers/class_provider.dart';

class AdminAiQueryScreen extends ConsumerStatefulWidget {
  const AdminAiQueryScreen({super.key});

  @override
  ConsumerState<AdminAiQueryScreen> createState() => _AdminAiQueryScreenState();
}

class _AdminAiQueryScreenState extends ConsumerState<AdminAiQueryScreen> {
  final _queryCtrl = TextEditingController();
  String? _selectedClassId;

  @override
  void dispose() {
    _queryCtrl.dispose();
    super.dispose();
  }

  Future<void> _ask() async {
    final q = _queryCtrl.text.trim();
    if (q.isEmpty) return;
    await ref
        .read(aiProvider.notifier)
        .ask(classId: _selectedClassId, queryText: q);
  }

  @override
  Widget build(BuildContext context) {
    final result = ref.watch(aiProvider);
    final classes = ref.watch(classListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Query'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(aiProvider.notifier).clear();
              _queryCtrl.clear();
            },
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // optional class filter
            classes.when(
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
              data: (list) => DropdownButtonFormField<String>(
                value: _selectedClassId,
                hint: const Text('Filter by class (optional)'),
                decoration: InputDecoration(
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8))),
                items: [
                  const DropdownMenuItem(
                      value: null, child: Text('All classes')),
                  ...list.map((c) =>
                      DropdownMenuItem(value: c.id, child: Text(c.className))),
                ],
                onChanged: (val) => setState(() => _selectedClassId = val),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _queryCtrl,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'e.g. Which students are at high risk in class A?',
                border:
                    OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 12),
            ElevatedButton.icon(
              onPressed: result is AsyncLoading ? null : _ask,
              icon: const Icon(Icons.psychology_outlined),
              label: const Text('Ask AI', style: TextStyle(fontSize: 15)),
            ),
            const SizedBox(height: 20),

            // result panel
            Expanded(
              child: result.when(
                data: (r) {
                  if (r == null)
                    return const Center(
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.psychology_outlined,
                            size: 52, color: Color(0xFFD1D5DB)),
                        SizedBox(height: 12),
                        Text('Ask a question about your students or classes',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                color: Color(0xFF9CA3AF), fontSize: 13)),
                      ]),
                    );

                  return SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // intent chip
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: const Color(0xFF1A56DB).withOpacity(0.1),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text('Intent: ${r.intent}',
                              style: const TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF1A56DB),
                                  fontWeight: FontWeight.w600)),
                        ),
                        const SizedBox(height: 8),
                        Text('Query: ${r.queryText}',
                            style: const TextStyle(
                                fontSize: 13, color: Color(0xFF6B7280))),
                        const SizedBox(height: 12),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(14),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Type: ${r.result.type}',
                                    style: const TextStyle(
                                        fontSize: 12,
                                        color: Color(0xFF6B7280))),
                                const SizedBox(height: 8),
                                Text(r.result.message,
                                    style: const TextStyle(
                                        fontSize: 14,
                                        color: Color(0xFF111827))),
                              ],
                            ),
                          ),
                        ),
                        if (r.actionLinks.isNotEmpty) ...[
                          const SizedBox(height: 12),
                          const Text('Actions',
                              style: TextStyle(
                                  fontSize: 13, fontWeight: FontWeight.w600)),
                          const SizedBox(height: 6),
                          ...r.actionLinks.map((a) => OutlinedButton(
                                onPressed: () => context.push(a.route),
                                child: Text(a.label),
                              )),
                        ],
                      ],
                    ),
                  );
                },
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(
                    child: Text(e.toString(),
                        style: const TextStyle(color: Colors.red))),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
