#version 330

uniform sampler2D tex;

in vec2 in_text;
out vec4 f_color;

void main(void)
{
	f_color = texture(tex, in_text);
	float r = f_color.r, g = f_color.g, b = f_color.b;
	float c = r + g + b;
	float p = sqrt(r * (r - g) + g * (g - b) + b * (b - r)) * 2.0;
	f_color *= sign(floor(p / (c + p) * 6.9));
}
