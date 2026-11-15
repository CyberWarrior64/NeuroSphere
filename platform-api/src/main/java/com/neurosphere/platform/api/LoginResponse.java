package com.neurosphere.platform.api;

import java.util.List;

public record LoginResponse(String access_token, String token_type, long expires_in, List<String> roles) {}
