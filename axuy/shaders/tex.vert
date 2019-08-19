#version 330

in vec2 in_vert;
out vec2 in_text;

void main(void)
{
	gl_Position = vec4(in_vert, 0.0, 1.0);
	in_text = in_vert * 0.5 + 0.5;
}
