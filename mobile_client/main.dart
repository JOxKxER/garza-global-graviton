import 'package:flutter/material.dart';

import 'mesh_client.dart';

void main() {
  runApp(const JokerApp());
}

class JokerApp extends StatelessWidget {
  const JokerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Joker Local AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF7EE787),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xFF10151A),
        useMaterial3: true,
      ),
      home: const JokerChatScreen(),
    );
  }
}

class JokerChatScreen extends StatefulWidget {
  const JokerChatScreen({super.key});

  @override
  State<JokerChatScreen> createState() => _JokerChatScreenState();
}

class _JokerChatScreenState extends State<JokerChatScreen> {
  final MeshClient _client = MeshClient();
  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_ChatMessage> _messages = <_ChatMessage>[
    const _ChatMessage(
      text: 'Online. Local mesh connected. What are we building?',
      fromJoker: true,
    ),
  ];

  bool _isSending = false;
  String? _conversationId;

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    _client.close();
    super.dispose();
  }

  Future<void> _sendMessage() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _isSending) {
      return;
    }

    _inputController.clear();
    setState(() {
      _messages.add(_ChatMessage(text: text, fromJoker: false));
      _isSending = true;
    });
    _scrollToBottom();

    try {
      final response = await _client.chat(
        text,
        conversationId: _conversationId,
      );
      final reply = _readReply(response);
      _conversationId = response['conversation_id']?.toString();
      if (!mounted) {
        return;
      }
      setState(() {
        _messages.add(_ChatMessage(text: reply, fromJoker: true));
      });
    } on MeshClientException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _messages.add(
          _ChatMessage(text: error.toString(), fromJoker: true, isError: true),
        );
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
        _scrollToBottom();
      }
    }
  }

  String _readReply(Map<String, dynamic> response) {
    final value = response['response'] ?? response['message'] ?? response['answer'];
    if (value == null) {
      return 'The backend returned no message.';
    }
    return value.toString();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Joker'),
            Text(
              'Local AI business partner',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Check backend health',
            onPressed: _checkHealth,
            icon: const Icon(Icons.favorite_outline),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  return _MessageBubble(message: _messages[index]);
                },
              ),
            ),
            if (_isSending) const LinearProgressIndicator(minHeight: 2),
            _Composer(
              controller: _inputController,
              enabled: !_isSending,
              onSend: _sendMessage,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _checkHealth() async {
    try {
      await _client.health();
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('FastAPI backend is online.')),
      );
    } on MeshClientException catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    }
  }
}

class _ChatMessage {
  const _ChatMessage({
    required this.text,
    required this.fromJoker,
    this.isError = false,
  });

  final String text;
  final bool fromJoker;
  final bool isError;
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final _ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final alignment = message.fromJoker
        ? CrossAxisAlignment.start
        : CrossAxisAlignment.end;
    final color = message.isError
        ? Theme.of(context).colorScheme.errorContainer
        : message.fromJoker
            ? const Color(0xFF1D2A24)
            : Theme.of(context).colorScheme.primaryContainer;

    return Column(
      crossAxisAlignment: alignment,
      children: [
        Text(
          message.fromJoker ? 'JOKER' : 'YOU',
          style: Theme.of(context).textTheme.labelSmall,
        ),
        Container(
          constraints: const BoxConstraints(maxWidth: 560),
          margin: const EdgeInsets.only(top: 4, bottom: 14),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(message.text),
        ),
      ],
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.enabled,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              enabled: enabled,
              minLines: 1,
              maxLines: 5,
              textInputAction: TextInputAction.newline,
              decoration: const InputDecoration(
                hintText: 'Message Joker...',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => onSend(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            tooltip: 'Send message',
            onPressed: enabled ? onSend : null,
            icon: const Icon(Icons.send),
          ),
        ],
      ),
    );
  }
}
