import 'dart:convert';

import 'package:http/http.dart' as http;

class MeshClientException implements Exception {
	const MeshClientException(this.message, {this.statusCode});

	final String message;
	final int? statusCode;

	@override
	String toString() => statusCode == null
			? 'MeshClientException: $message'
			: 'MeshClientException ($statusCode): $message';
}

class MeshClient {
	MeshClient({
		String baseUrl = 'http://127.0.0.1:8000',
		http.Client? httpClient,
	})  : baseUrl = baseUrl.replaceFirst(RegExp(r'/*$'), ''),
				_httpClient = httpClient ?? http.Client();

	final String baseUrl;
	final http.Client _httpClient;

	Future<Map<String, dynamic>> health() async {
		return getJson('/health');
	}

	Future<Map<String, dynamic>> getJson(String path) async {
		final response = await _send(() => _httpClient.get(_uri(path)));
		return _decodeObject(response);
	}

	Future<Map<String, dynamic>> postJson(
		String path,
		Map<String, dynamic> body,
	) async {
		final response = await _send(
			() => _httpClient.post(
				_uri(path),
				headers: const {'Content-Type': 'application/json'},
				body: jsonEncode(body),
			),
		);
		return _decodeObject(response);
	}

	Future<Map<String, dynamic>> chat(
		String message, {
		String? conversationId,
	}) {
		return postJson('/chat', {
			'message': message,
			if (conversationId != null) 'conversation_id': conversationId,
		});
	}

	void close() => _httpClient.close();

	Uri _uri(String path) {
		final normalizedPath = path.startsWith('/') ? path : '/$path';
		return Uri.parse('$baseUrl$normalizedPath');
	}

	Future<http.Response> _send(Future<http.Response> Function() request) async {
		try {
			final response = await request();
			if (response.statusCode < 200 || response.statusCode >= 300) {
				throw MeshClientException(
					_errorMessage(response),
					statusCode: response.statusCode,
				);
			}
			return response;
		} on MeshClientException {
			rethrow;
		} on Exception catch (error) {
			throw MeshClientException('Unable to reach $baseUrl: $error');
		}
	}

	Map<String, dynamic> _decodeObject(http.Response response) {
		final decoded = jsonDecode(response.body);
		if (decoded is! Map<String, dynamic>) {
			throw const MeshClientException('Expected a JSON object response.');
		}
		return decoded;
	}

	String _errorMessage(http.Response response) {
		try {
			final decoded = jsonDecode(response.body);
			if (decoded is Map<String, dynamic> && decoded['detail'] != null) {
				return decoded['detail'].toString();
			}
		} on FormatException {
			// Fall through to the raw response body.
		}
		return response.body.isEmpty ? 'Request failed.' : response.body;
	}
}
