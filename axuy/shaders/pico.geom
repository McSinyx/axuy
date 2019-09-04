#version 330
layout (triangles) in;
layout (triangle_strip, max_vertices = 81) out;

uniform float visibility;
uniform vec3 camera;
uniform mat4 vp;

out float intensity;

void translate(inout vec4 delta)
{
	vec4 vert;
	float dist;
	for (int n = 0; n < 3; ++n) {
		vert = gl_in[n].gl_Position + delta;
		dist = distance(camera, vec3(vert));
		intensity = 1 / (1 + dist * dist / visibility);
		gl_Position = vp * vert;
		EmitVertex();
	}
	EndPrimitive();
}

void main()
{
	float i, j, k;
	for (i = -12.0; i < 12.3; i += 12.0)
		for (j = -12.0; j < 12.3; j += 12.0)
			for (k = -9.0; k < 12.3; k += 9.0)
				translate(vec4(i, j, k, 0.0));
}
