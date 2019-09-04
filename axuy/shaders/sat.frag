#version 330

uniform sampler2D tex;

in vec2 in_text;

void main(void)
{
	gl_FragColor = texture(tex, in_text) * 0.69;
	float r = gl_FragColor.r, g = gl_FragColor.g, b = gl_FragColor.b;
	gl_FragColor *= abs(r - g) + abs(g - b) + abs(b - r);
	gl_FragColor -= r * g * b * 4.2;
}
