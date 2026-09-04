using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

/// <summary>
/// 벤치마크용 Windows 빌드를 배치 모드에서 만든다.
///
/// 저장소에 빌드 스크립트가 없어서 여기 둔다. 이 클래스가 하는 일은 하나뿐이다 —
/// `EditorBuildSettings` 에 이미 켜져 있는 씬을 그대로 모아 `BuildOptions.Development`
/// 로 굽는 것.
///
/// **`Development` 가 이 스크립트의 요점이다.** SDK 의 `ArtelManager.SpawnInDevelopmentBuilds`
/// 가 development build 에서만 자기를 붙이므로, 이 플래그가 빠지면 씬에 아무것도 안 넣은
/// 빌드는 SDK 없이 켜지고 `artel game start` 가 60초 뒤 `game_registration_timeout` 으로
/// 죽는다. 그 실패는 서버 쪽 로그에 아무 단서도 남기지 않는다.
///
/// 출력 경로는 `-artelBuildPath` 로 받는다. 배치 모드에서 실행할 때 인자로 넘어온다.
/// </summary>
public static class ArtelBenchBuild
{
    private const string PathArgument = "-artelBuildPath";

    public static void BuildWindows64()
    {
        var output = ReadPathArgument();
        if (string.IsNullOrWhiteSpace(output))
        {
            Fail($"{PathArgument} 인자가 없다. 빌드 산출물을 어디에 둘지 정해서 다시 부른다.");
            return;
        }

        var scenes = EditorBuildSettings.scenes
            .Where(scene => scene.enabled)
            .Select(scene => scene.path)
            .ToArray();

        if (scenes.Length == 0)
        {
            Fail("EditorBuildSettings 에 켜진 씬이 하나도 없다.");
            return;
        }

        Debug.Log($"[ArtelBenchBuild] 씬 {scenes.Length}개를 {output} 으로 굽는다.");
        foreach (var scene in scenes)
        {
            Debug.Log($"[ArtelBenchBuild]   {scene}");
        }

        var options = new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = output,
            target = BuildTarget.StandaloneWindows64,
            targetGroup = BuildTargetGroup.Standalone,
            // Development 없이 구우면 SDK 가 안 붙는다. 위 클래스 주석 참조.
            options = BuildOptions.Development,
        };

        var report = BuildPipeline.BuildPlayer(options);
        var summary = report.summary;

        if (summary.result == BuildResult.Succeeded)
        {
            Debug.Log(
                $"[ArtelBenchBuild] 성공 — {summary.totalSize} bytes, {summary.totalTime}");
            EditorApplication.Exit(0);
            return;
        }

        Fail($"빌드 실패 — result={summary.result}, errors={summary.totalErrors}");
    }

    private static string ReadPathArgument()
    {
        var args = Environment.GetCommandLineArgs();
        for (var i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == PathArgument)
            {
                return args[i + 1];
            }
        }
        return null;
    }

    private static void Fail(string message)
    {
        Debug.LogError($"[ArtelBenchBuild] {message}");
        EditorApplication.Exit(1);
    }
}
