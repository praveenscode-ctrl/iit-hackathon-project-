class ActionLink {
  final String label;
  final String route;

  ActionLink({required this.label, required this.route});

  factory ActionLink.fromJson(Map<String, dynamic> j) => ActionLink(
        label: j['label'] as String,
        route: j['route'] as String,
      );
}

class AiResult {
  final String type;
  final List<dynamic> data;
  final String message;

  AiResult({required this.type, required this.data, required this.message});

  factory AiResult.fromJson(Map<String, dynamic> j) => AiResult(
        type: j['type'] as String,
        data: j['data'] as List,
        message: j['message'] as String,
      );
}

class AiResponseModel {
  final String intent;
  final String queryText;
  final AiResult result;
  final List<ActionLink> actionLinks;

  AiResponseModel({
    required this.intent,
    required this.queryText,
    required this.result,
    required this.actionLinks,
  });

  factory AiResponseModel.fromJson(Map<String, dynamic> j) => AiResponseModel(
        intent: j['intent'] as String,
        queryText: j['query_text'] as String,
        result: AiResult.fromJson(j['result'] as Map<String, dynamic>),
        actionLinks: (j['action_links'] as List)
            .map((e) => ActionLink.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
