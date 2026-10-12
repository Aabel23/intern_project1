// JVM harness for the app's pure-Kotlin protocol files: runs ClaimProtocol and FlexJson
// against the Python machine implementation (tests/machine/test_kotlin_interop.py).
plugins {
    kotlin("jvm") version "2.1.0"
    application
}

repositories { mavenCentral() }

dependencies {
    implementation("org.bouncycastle:bcprov-jdk15to18:1.86")
    implementation("org.json:json:20240303")
}

// Uses the JDK on PATH (no toolchain download in CI sandboxes).
kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
java { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }

sourceSets {
    main {
        kotlin.srcDir("../../flutter_app/android/app/src/main/kotlin")
        kotlin.include("**/FlexJson.kt", "**/ClaimProtocol.kt", "**/InteropMain.kt")
    }
}

application { mainClass.set("com.example.simple_app.InteropMainKt") }
